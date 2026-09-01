/**
 * 患者展示 - 排队叫号系统
 * 简洁大气 干净美观
 */

// 根据当前 hostname 获取 API 和 WebSocket 地址
function getApiConfig() {
    const host = window.location.hostname;
    const portMap = {
        'oa.nsyy.com.cn':  6080,
        '192.168.3.12':    6080,
        '192.168.124.9':   8081,
        '127.0.0.1':   8081,
        'localhost':   8081,
    };
    let port = portMap[host];
    if (!port) {
        // 模糊匹配：如果包含 192.168.124 则用 8080（或自定义规则）
        if (host.includes('192.168.124')) {
            port = 8081;
        } else {
            port = 8081; // 默认值
        }
    }
    return {
        apiBase: `http://${host}:${port}/mz`,
        wsUrl: `ws://${host}:${port}/mz`
    };

}

// 根据当前环境生成配置
const config = getApiConfig();
const API_BASE = config.apiBase;
const WS_URL = config.wsUrl;

let currentWindowId = 1;
let ws = null;
let refreshTimer = null;
let businessTypes = {};
let windows = {};
let currentWindowInfo = null;

// 缓存当前显示数据
let cachedCurrentCall = null;
let cachedQueues = [];

// ==================== 控制标志 ====================
let isInitializing = true;        // 初始化阶段，下拉框事件忽略
let isSwitching = false;          // 切换窗口锁
let isClosing = false;            // 主动关闭 ws，防止 onclose 重连

// 在文件顶部增加心跳定时器变量
let heartbeatTimer = null;
let lastMessageTime = Date.now();
let watchdogTimer = null;

// ==================== 辅助函数：标准化API响应 ====================
function normalizeQueueStatus(rawData) {
    // 处理常见的包裹格式：{ code: 0, data: {...} } 或直接返回数据
    let data = rawData;
    if (rawData && typeof rawData === 'object') {
        // 如果存在 data 字段且是对象，则取 data
        if (rawData.data && typeof rawData.data === 'object' && !rawData.current_calls && !rawData.business_status) {
            data = rawData.data;
        }
    }

    // 确保数据结构完整
    return {
        current_calls: data.current_calls || [],
        business_status: data.business_status || {}
    };
}

// ==================== 初始化 ====================
document.addEventListener('DOMContentLoaded', () => {
    init();

    // 窗口切换
    document.getElementById('windowSelect').addEventListener('change', (e) => {
        if (isInitializing) return;
        const newWindowId = parseInt(e.target.value);
        switchWindow(newWindowId);
    });

    // 页面关闭前清理
    window.addEventListener('beforeunload', () => {
        if (refreshTimer) clearInterval(refreshTimer);
        if (ws) ws.close();
    });
});

async function init() {
    isInitializing = true;
    try {
        // 安全读取 localStorage // 恢复上次窗口ID
        let windowId = null;
        try {
            if (typeof localStorage !== 'undefined' && localStorage !== null) {
                const stored = localStorage.getItem('currentWindowId');
                if (stored) windowId = parseInt(stored);
            }
        } catch (e) {
            console.warn('localStorage 不可用，使用默认值', e);
        }

        if (!windowId || isNaN(windowId)) {
            const urlParams = new URLSearchParams(window.location.search);
            windowId = parseInt(urlParams.get('windowId')) || 1;
        }

        // 确保窗口列表先加载
        await loadWindows();
        await switchWindow(windowId);

        // 检查 androidTTS 是否注入
        console.log('androidTTS 对象:', typeof window.androidTTS);
        if (typeof window.androidTTS !== 'undefined') {
            console.log('androidTTS.isReady:', window.androidTTS.isReady());
        } else {
            console.warn('androidTTS 未定义！');
        }
        console.log('当前窗口ID:', currentWindowId);
    } finally {
        isInitializing = false;
    }
}

// ==================== 窗口加载 ====================
async function loadWindows(retryCount = 0) {
    try {
        const response = await fetch(`${API_BASE}/windows`);
        if (response.ok) {
            windows = await response.json();
            updateWindowSelect(windows);
            return true;
        } else {
            throw new Error(`HTTP ${response.status}`);
        }
    } catch (error) {
        console.error('加载窗口数据失败:', error);
        if (retryCount < 3) {
            await new Promise(resolve => setTimeout(resolve, 2000));
            return loadWindows(retryCount + 1);
        } else {
            const select = document.getElementById('windowSelect');
            if (select) {
                select.innerHTML = `<option value="">加载失败，请检查网络</option>`;
                const retryBtn = document.createElement('button');
                retryBtn.textContent = '重试';
                retryBtn.onclick = () => location.reload();
                select.parentNode.appendChild(retryBtn);
            }
            return false;
        }
    }
}

function updateWindowSelect(windows) {
    const select = document.getElementById('windowSelect');
    if (!select) return;
    select.innerHTML = '';
    for (const [id, info] of Object.entries(windows)) {
        const option = document.createElement('option');
        option.value = id;
        option.textContent = info.window_name;
        select.appendChild(option);
    }
}

// ==================== 窗口切换 ====================
async function switchWindow(windowId) {
    // 防重入
    if (isSwitching) {
        console.warn('switchWindow 正在执行，跳过本次调用');
        return;
    }

    // 如果目标窗口未加载，先加载
    if (!windows || Object.keys(windows).length === 0) {
        await loadWindows();
    }

    // 如果目标窗口 ID 无效，或与当前相同
    if (!windowId) {
        console.warn('无效窗口 ID');
        return;
    }

    // 如果与当前窗口相同，检查 WebSocket 是否已连接，未连接则建立
    if (windowId === currentWindowId) {
        console.log('目标窗口与当前相同，检查 WebSocket 状态');
        if (!ws || ws.readyState !== WebSocket.OPEN) {
            console.log('WebSocket 未连接，初始化');
            initWebSocket();
            startAutoRefresh();
        }
        return;
    }

    // 锁定，避免并发
    isSwitching = true;
    isClosing = true;      // 标记主动关闭，防止 onclose 自动重连

    try {
        // 1. 清理旧资源
        if (refreshTimer) {
            clearInterval(refreshTimer);
            refreshTimer = null;
        }
        if (heartbeatTimer) {
            clearInterval(heartbeatTimer);
            heartbeatTimer = null;
        }
        if (ws) {
            ws.close();
            ws = null;
        }
        // 2. 更新 currentWindowId
        currentWindowId = windowId;
        currentWindowInfo = windows[windowId] || null;

        // 3. 持久化
        try {
            if (typeof localStorage !== 'undefined' && localStorage !== null) {
                localStorage.setItem('currentWindowId', windowId);
            }
        } catch (e) {}

        // 4. UI 同步
        if (!currentWindowInfo) {
            const select = document.getElementById('windowSelect');
            const selectedOption = select && select.querySelector(`option[value="${windowId}"]`);
            const windowName = (selectedOption && selectedOption.textContent) || `窗口${windowId}`;
            document.getElementById('windowName').textContent = windowName;
            document.getElementById('systemTitle').textContent = windowName;
        } else {
            document.getElementById('windowName').textContent = currentWindowInfo.window_name;
            document.getElementById('systemTitle').textContent = currentWindowInfo.window_name;
        }
        document.getElementById('windowSelect').value = windowId;

        // 5. 重置显示缓存和当前叫号显示
        cachedCurrentCall = null;
        updateCurrentCallDisplay('---', '等待叫号');

        // 6. 重新加载数据
        await loadQueueStatus();

        // 7. 延迟一帧创建 WebSocket 和自动刷新
        requestAnimationFrame(() => {
            // 在创建新连接前，重置主动关闭标志（因为新连接不再是主动关闭）
            // isClosing = false;
            initWebSocket();
            startAutoRefresh();
        });

    } finally {
        // 解锁，但注意 isClosing 在 requestAnimationFrame 中被重置，但在那之前保持 true
        isSwitching = false;
        // 注意：isClosing 会在新连接建立前重置，但这里为了防止某些异常，可以重置
        // 但为了安全，我们不在这里重置，让 requestAnimationFrame 处理
    }
}

// ==================== 队列状态加载 ====================
async function loadQueueStatus() {
    try {
        const response = await fetch(`${API_BASE}/api/queue/status`);
        if (response.ok) {
            const rawData = await response.json();
            const normalizedData = normalizeQueueStatus(rawData);
            updateDisplay(normalizedData);
        } else {
            showError();
        }
    } catch (error) {
        console.error('加载队列状态失败:', error);
        showError();
    }
}

function showError() {
    updateCurrentCallDisplay('---', '等待叫号');
}

// ==================== 更新显示 - 增量更新（无数据真空期） ====================
function updateDisplay(data) {
    // 更新当前叫号
    if (data.current_calls && data.current_calls.length > 0) {
        // 使用严格相等，确保类型匹配
        const windowCall = data.current_calls.find(call => Number(call.window_id) === Number(currentWindowId));
        if (windowCall) {
            // 检查是否真的变化了
            const newCallKey = `${windowCall.queue_number}_${windowCall.patient_name}`;
            const cachedKey = cachedCurrentCall ? `${cachedCurrentCall.queue_number}_${cachedCurrentCall.patient_name}` : null;
            if (cachedKey !== newCallKey) {
                updateCurrentCallDisplay(windowCall.queue_number, windowCall.patient_name || '--');
                animateCall();
                cachedCurrentCall = windowCall;
            }
        } else {
            // 当前窗口没有叫号，但之前有显示
            if (cachedCurrentCall) {
                updateCurrentCallDisplay('---', '暂无叫号');
                cachedCurrentCall = null;
            }
        }
    } else {
        // 没有任何叫号
        if (cachedCurrentCall) {
            updateCurrentCallDisplay('---', '暂无叫号');
            cachedCurrentCall = null;
        }
    }

}

function updateCurrentCallDisplay(queueNumber, patientName) {
    const numberElement = document.getElementById('callNumber');
    const patientElement = document.getElementById('patientName');

    if (numberElement) {
        patientElement.textContent = patientName || '请等待';
    }

    if (patientElement) {
        numberElement.textContent = queueNumber || '---';
    }
}


// 简单的防XSS辅助函数
function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>]/g, function(m) {
        if (m === '&') return '&amp;';
        if (m === '<') return '&lt;';
        if (m === '>') return '&gt;';
        return m;
    });
}

// ==================== WebSocket ====================
function initWebSocket() {
    // 重置主动关闭标志（因为新连接）
    isClosing = false;
    // 如果已经存在打开的 ws，先关闭（但通常调用前已关闭）
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close();
        ws = null;
    }
    // 清除旧的心跳定时器，防止切换窗口时残留
    if (heartbeatTimer) {
        clearInterval(heartbeatTimer);
        heartbeatTimer = null;
    }

    ws = new WebSocket(`${WS_URL}/ws/window/${currentWindowId}`);

    ws.onopen = () => {
        console.log('WebSocket连接成功');
        // 1. 开启心跳定时器（15秒间隔）
        heartbeatTimer = setInterval(() => {
            if (ws && ws.readyState === WebSocket.OPEN) {
                try {
                    // 发送心跳，注意格式：如果后端只认 'ping' 字符串则发字符串，若认 JSON 则改
                    ws.send('ping');
                    console.log('心跳 ping 发送');
                } catch (e) {
                    console.warn('发送心跳异常', e);
                }
            } else {
                // 如果连接已断开，清除定时器，避免内存泄露
                clearInterval(heartbeatTimer);
                heartbeatTimer = null;
            }
        }, 15000); // 15秒

        try {
            ws.send(JSON.stringify({ action: 'get_status' }));
        } catch(e) {
            ws.send('get_status');
        }

        // 在 initWebSocket 的 onopen 末尾添加：
        watchdogTimer = setInterval(() => {
            if (ws && ws.readyState === WebSocket.OPEN) {
                const now = Date.now();
                // 如果超过 30 秒没有收到任何消息（包括 Pong），认为连接已死
                if (now - lastMessageTime > 30000) {
                    console.warn('WebSocket 长时间未收到消息，强制重连');
                    isClosing = false; // 确保重连
                    ws.close(); // 触发 onclose 重连
                    clearInterval(watchdogTimer);
                    watchdogTimer = null;
                }
            }
        }, 5000);

    };

    ws.onmessage = (event) => {
        lastMessageTime = Date.now(); // 新增这一行
        console.log('=== 收到原始 WebSocket 消息 ===', event.data);  // 新增
        // 处理 pong
        if (event.data === 'pong') {
            console.log('收到 pong');
            return;
        }
        try {
            const data = JSON.parse(event.data);
            handleWebSocketMessage(data);
        } catch (e) {
            console.warn('WebSocket消息解析失败:', e);
        }
    };

    ws.onclose = () => {
        console.log('WebSocket断开');
        if (!isClosing) {
            console.log('3秒后重连');
            setTimeout(() => initWebSocket(), 3000);
        } else {
            console.log('主动关闭，不重连');
        }
    };
    ws.onerror = (error) => {
        console.error('WebSocket错误:', error);
    };
}

function handleWebSocketMessage(data) {
    console.log('当前窗口ID:', currentWindowId);
    console.log('接收到socket消息:', data);
    console.log('接收到socket消息:', data.type);
    // 处理不同类型的消息
    const messageData = data.data || data;

    switch (data.type) {
        case 'init':
        case 'status':
        case 'test':
            console.log('接收到 test socket消息:', messageData);
            break
        case 'call_success':
            // 更新当前叫号
            if (messageData && messageData.queue_number) {
                updateCurrentCallDisplay(messageData.queue_number, messageData.patient_name || '--');
                animateCall();
                // 更新缓存
                cachedCurrentCall = {
                    queue_number: messageData.queue_number,
                    patient_name: messageData.patient_name,
                    window_id: currentWindowId
                };
            } else if (messageData && messageData.current_call) {
                const call = messageData.current_call;
                updateCurrentCallDisplay(call.queue_number, call.patient_name || '--');
                animateCall();
                cachedCurrentCall = {
                    queue_number: call.queue_number,
                    patient_name: call.patient_name,
                    window_id: currentWindowId
                };
            } else if (cachedCurrentCall) {
                updateCurrentCallDisplay('---', '暂无叫号');
                cachedCurrentCall = null;
            }
            // 刷新队列
            loadQueueStatus();
            break;

        case 'call':
        case 'complete':
        case 'skip':
        case 'queue_update':
            console.log('收到队列更新消息:', messageData);
            loadQueueStatus();
            break;
        case 'tts_call':
            console.log('语音叫号:', messageData);
            showToast('socket 语音叫号');
            speakWithNative(messageData.queue_number, messageData.patient_name || '--');
            break;
        default:
            // 未知消息类型，尝试刷新
            if (messageData && messageData.queue_number) {
                updateCurrentCallDisplay(messageData.queue_number, messageData.patient_name || '--');
                animateCall();
            }
            loadQueueStatus();
            break;
    }
}

function animateCall() {
    const callDisplay = document.querySelector('.current-call-display');
    if (callDisplay) {
        callDisplay.classList.add('calling-animation');
        setTimeout(() => callDisplay.classList.remove('calling-animation'), 2000);
    }
}

// ==================== 自动刷新 ====================
function startAutoRefresh() {
    if (refreshTimer) clearInterval(refreshTimer);
    refreshTimer = setInterval(loadQueueStatus, 1000*60);
}

// ==================== 调用android 广告机 TTS进行语音播报 ====================

function speakWithNative1(queueNumber, patientName) {
    console.log('调用android TTS进行语音播报:', queueNumber, patientName);
    const windowName = (currentWindowInfo && currentWindowInfo.window_name) || '窗口';
    const text = patientName && patientName.trim()
        ? `请 ${patientName}，到${windowName}办理业务`
        : `请${queueNumber}号，到${windowName}办理业务`;
    if (typeof window.androidTTS !== 'undefined') {
        window.androidTTS.speak(text);
    } else {
        showToast('当前环境不支持原生TTS调用');
    }
}

function speakWithNative1(queueNumber, patientName, retries = 3) {
    const windowName = (currentWindowInfo && currentWindowInfo.window_name) || '窗口';
    const text = patientName && patientName.trim()
        ? `请 ${patientName}，到${windowName}办理业务`
        : `请${queueNumber}号，到${windowName}办理业务`;

    function trySpeak(attempt) {
        if (typeof window.androidTTS === 'undefined') {
            showToast('不支持TTS');
            return;
        }
        // 调用 speak 并检查返回值（需配合 Android 端返回 boolean）
        // 注意：需要修改 TTSJSInterface.speak 返回 boolean
        var success = window.androidTTS.speak(text);
        if (success) {
            console.log('语音播报成功');
            return;
        }
        if (attempt > 0) {
            // 200ms 后重试，保证实时性
            setTimeout(() => trySpeak(attempt - 1), 200);
        } else {
            console.warn('语音播报失败，患者可看屏幕文字');
        }
    }
    trySpeak(retries);
}


function showToast(message) {
    // 简单提示，可使用 alert 或自定义轻提示
    console.warn(message);
    // 更友好的方式：在页面顶部显示临时消息
    const toast = document.createElement('div');
    toast.textContent = message;
    toast.style.position = 'fixed';
    toast.style.bottom = '20px';
    toast.style.left = '50%';
    toast.style.transform = 'translateX(-50%)';
    toast.style.backgroundColor = 'rgba(0,0,0,0.8)';
    toast.style.color = '#fff';
    toast.style.padding = '8px 16px';
    toast.style.borderRadius = '8px';
    toast.style.zIndex = '10000';
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 2000);
}

