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

// 缓存当前显示数据，用于增量更新
let cachedCurrentCall = null;

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
        // 最多重试 3 次，每次间隔 2 秒
        if (retryCount < 3) {
            await new Promise(resolve => setTimeout(resolve, 2000));
            return loadWindows(retryCount + 1);
        } else {
            // 显示错误提示
            const select = document.getElementById('windowSelect');
            if (select) {
                select.innerHTML = `<option value="">加载失败，请检查网络</option>`;
                // 添加重试按钮
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
    // 如果窗口未加载，先加载
    if (!windows || Object.keys(windows).length === 0) {
        await loadWindows();
    }

    if (!windowId || windowId === currentWindowId) return;

    // ✅ 1. 立即持久化
    currentWindowId = windowId;
//    localStorage.setItem('currentWindowId', windowId);
    currentWindowInfo = windows[windowId];
    try {
        if (typeof localStorage !== 'undefined' && localStorage !== null) {
            localStorage.setItem('currentWindowId', windowId);
        }
    } catch (e) {}

    // ✅ 2. UI 同步
    if (!currentWindowInfo) {
        const select = document.getElementById('windowSelect');
        const selectedOption = select?.querySelector(`option[value="${windowId}"]`);
        const windowName = selectedOption?.textContent || `窗口${windowId}`;
        document.getElementById('windowName').textContent = windowName;
        document.getElementById('systemTitle').textContent = windowName;
    } else {
        document.getElementById('windowName').textContent = currentWindowInfo.window_name;
        document.getElementById('systemTitle').textContent = currentWindowInfo.window_name;
    }
    document.getElementById('windowSelect').value = windowId;

    // ✅ 3. 清理旧资源
    if (refreshTimer) {
        clearInterval(refreshTimer);
        refreshTimer = null;
    }

    if (ws) {
        ws.close();
        ws = null;
    }

    // ✅ 4. 重置显示缓存和当前叫号显示
    cachedCurrentCall = null;
    updateCurrentCallDisplay('---', '等待叫号');

    // ✅ 5. 重新加载数据
    await loadQueueStatus();

    // ✅ 6. 延迟一帧创建 WebSocket（非常关键）
    requestAnimationFrame(() => {
        initWebSocket();
        startAutoRefresh();
    });
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
    updateCurrentCallDisplay('---', '系统维护中');
    updateQueueList([]);
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

    // 更新等待队列
    updateQueue(data);
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

function updateQueue(data) {
    let totalWaiting = 0;
    const allQueues = [];

    if (data.business_status) {
        for (const [business, status] of Object.entries(data.business_status)) {
            if (status.waiting_queues) {
                totalWaiting += status.waiting_count || 0;
                allQueues.push(...status.waiting_queues);
            }
        }
    }

    // 更新等待人数
    const queueCount = document.getElementById('queueCount');
    if (queueCount) {
        queueCount.textContent = `${totalWaiting}人`;
    }

    // 更新队列列表
    updateQueueList(allQueues);
}

// 缓存当前队列数据
let cachedQueues = [];

function updateQueueList(queues) {
    const container = document.getElementById('queueList');
    if (!container) return;

    const newQueues = (queues || []).slice(0, 12);

    // 如果数据没变，不更新
    const newQueueNumbers = new Set(newQueues.map(q => q.queue_number));
    const cachedQueueNumbers = new Set(cachedQueues.map(q => q.queue_number));

    if (newQueueNumbers.size === cachedQueueNumbers.size &&
        [...newQueueNumbers].every(num => cachedQueueNumbers.has(num))) {
        // 数据完全相同，跳过更新
        return;
    }

    // 使用增量更新
    // 1. 构建现有DOM元素Map
    const existingItems = container.querySelectorAll('.queue-item');
    const existingMap = new Map();
    existingItems.forEach(item => {
        existingMap.set(item.dataset.queueNumber, item);
    });

    // 2. 删除不再存在的项
    existingItems.forEach(item => {
        if (!newQueueNumbers.has(item.dataset.queueNumber)) {
            item.remove();
        }
    });

    // 3. 添加或更新项
    const fragment = document.createDocumentFragment();
    newQueues.forEach(queue => {
        const existingItem = existingMap.get(queue.queue_number);
        if (existingItem) {
            container.appendChild(existingItem);
        } else {
            const item = document.createElement('div');
            item.className = 'queue-item';
            item.dataset.queueNumber = queue.queue_number;
            item.innerHTML = `
                <div class="queue-number">${escapeHtml(queue.queue_number)}</div>
                <div class="queue-label">等待中</div>
            `;
            fragment.appendChild(item);
        }
    });

    if (fragment.children.length > 0) {
        container.appendChild(fragment);
    }

    // 4. 如果没有等待患者
    if (newQueues.length === 0 && container.querySelectorAll('.queue-item').length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"/>
                    <path d="M8 14s1.5 2 4 2 4-2 4-2"/>
                    <line x1="9" y1="9" x2="9.01" y2="9"/>
                    <line x1="15" y1="9" x2="15.01" y2="9"/>
                </svg>
                <span>暂无等待患者</span>
            </div>
        `;
    }

    // 更新缓存
    cachedQueues = newQueues;
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
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close();
    }

    ws = new WebSocket(`${WS_URL}/ws/window/${currentWindowId}`);

    ws.onopen = () => {
        console.log('WebSocket连接成功');
        // 发送更规范的消息格式（兼容两种格式）
        try {
            ws.send(JSON.stringify({ action: 'get_status' }));
        } catch(e) {
            ws.send('get_status');
        }
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            handleWebSocketMessage(data);
        } catch (e) {
            if (event.data === 'pong') return;
            console.warn('WebSocket消息解析失败:', e);
        }
    };

    ws.onclose = () => {
        console.log('WebSocket断开，3秒后重连');
        setTimeout(() => initWebSocket(), 3000);
    };

    ws.onerror = (error) => {
        console.error('WebSocket错误:', error);
    };
}

function handleWebSocketMessage(data) {
    console.log('接收到socket消息:', data);
    console.log('接收到socket消息:', data.type);
    // 处理不同类型的消息
    const messageData = data.data || data;

    switch (data.type) {
        case 'init':
        case 'status':
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
    refreshTimer = setInterval(loadQueueStatus, 5000);
}

// ==================== 调用android 广告机 TTS进行语音播报 ====================
function speakWithNative(queueNumber, patientName) {
    console.log('调用android TTS进行语音播报:', queueNumber, patientName);
    text = patientName && patientName.trim()
        ? `请${queueNumber}号，${patientName}，到${currentWindowInfo?.window_name || '窗口'}办理业务`
        : `请${queueNumber}号，到${currentWindowInfo?.window_name || '窗口'}办理业务`;
    if (typeof window.androidTTS !== 'undefined') {
        // 检查是否就绪（可选）
        if (window.androidTTS.isReady && window.androidTTS.isReady()) {
            window.androidTTS.speak(text);
        } else {
            showToast('原生TTS尚未初始化，请稍后重试');
        }
    } else {
        showToast('当前环境不支持原生TTS调用');
    }
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

