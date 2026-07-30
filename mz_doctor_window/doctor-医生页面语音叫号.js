/**
 * 医生窗口 - 排队叫号系统
 * 简洁大气 干净美观
 */

// 配置
const API_BASE = 'http://192.168.124.9:8000';
const WS_URL = `ws://192.168.124.9:8000`;
//const API_BASE = 'http://192.168.3.12:8000';
//const WS_URL = `ws://192.168.3.12:8000`;

let currentWindowId = 1;
let currentWindowInfo = null;
let ws = null;
let currentCall = null;
let businessTypes = {};
let windows = {};
let refreshTimer = null;
let currentBusinessType = null;
let isCalling = false;  // 防止重复调用叫号接口

let refreshDebounceTimer = null;  // 防抖定时器
const REFRESH_INTERVAL = 15000;  // 刷新间隔 15 秒
const DEBOUNCE_DELAY = 2000;     // 防抖延迟 2 秒

// 缓存当前数据，用于增量更新
let cachedBusinessStatus = {};
let cachedQueueLists = {};

// ==================== 初始化 ====================
document.addEventListener('DOMContentLoaded', () => {
    init();

    // 按钮事件绑定
    document.getElementById('switchWindowBtn').addEventListener('click', () => {
        const newWindowId = parseInt(document.getElementById('windowSelect').value);
        switchWindow(newWindowId);
    });

    document.getElementById('completeBtn').addEventListener('click', completeService);
    document.getElementById('skipBtn').addEventListener('click', skipCurrent);
    document.getElementById('recallBtn').addEventListener('click', recallCurrent);

    // 页面关闭前清理
    window.addEventListener('beforeunload', () => {
        if (refreshTimer) clearInterval(refreshTimer);
        if (ws) ws.close();
    });
});

async function init() {
    // 恢复上次窗口ID
    let windowId = parseInt(localStorage.getItem('currentWindowId'));
    if (!windowId || isNaN(windowId)) {
        const urlParams = new URLSearchParams(window.location.search);
        windowId = parseInt(urlParams.get('windowId')) || 1;
    }

    await loadBusinessTypes();
    await loadWindows();
    await switchWindow(windowId);

    // 创建激活按钮（仅当语音不可用时显示，但这里直接作为保险）
    const activateBtn = document.createElement('button');
    activateBtn.textContent = '🔊 点击启用语音';
    activateBtn.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        z-index: 9999;
        background: #3B82F6;
        color: white;
        border: none;
        border-radius: 40px;
        padding: 10px 20px;
        font-size: 14px;
        cursor: pointer;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    `;
    activateBtn.onclick = () => {
        // 尝试播放空白语音
        const silent = new SpeechSynthesisUtterance(' ');
        window.speechSynthesis.speak(silent);
        // 再播放一个测试语音
        const test = new SpeechSynthesisUtterance('语音已启用，可以正常叫号了');
        test.lang = 'zh-CN';
        window.speechSynthesis.speak(test);
        activateBtn.remove();
        showToast('语音已启用，现在叫号会有声音了');
    };
    document.body.appendChild(activateBtn);
}

// ==================== 业务类型加载 ====================
async function loadBusinessTypes() {
    try {
        const response = await fetch(`${API_BASE}/business-types`);
        if (response.ok) {
            businessTypes = await response.json();
        } else {
            businessTypes = getDefaultBusinessTypes();
        }
    } catch (error) {
        businessTypes = getDefaultBusinessTypes();
    }
}

function getDefaultBusinessTypes() {
    return {
            "1": {
                'name': '门诊取药',
                'type': 'medicine',
                'windows': [],
                'prefix': 'A',
                'color': '#e74c3c',
                'description': '含药品查询缴费',
                'icon': '💊',
                'voice': 'A'
            },
            "2": {
                'name': '打印病历',
                'type': 'record',
                'windows': [],
                'prefix': 'B',
                'color': '#3498db',
                'description': '病历打印服务',
                'icon': '📄',
                'voice': 'B'
            },
            "3": {
                'name': '医院缴费',
                'type': 'payment',
                'windows': [],
                'prefix': 'C',
                'color': '#f39c12',
                'description': '医疗费用缴纳',
                'icon': '💰',
                'voice': 'C'
            },
            "4": {
                'name': '工伤结算/用血报销',
                'type': 'payment',
                'windows': ['8'],
                'prefix': 'C',
                'color': '#f39c12',
                'description': '工伤结算/用血减免报销业务处理，在3号缴费窗口独立办理',
                'icon': '💰',
                'voice': 'C'
            }
        };
}

async function loadWindows() {
    try {
        const response = await fetch(`${API_BASE}/windows`);
        if (response.ok) {
            windows = await response.json();
            updateWindowSelect(windows);
        } else {
            // API 不可用时显示默认选项
            updateWindowSelect({});
        }
    } catch (error) {
        console.error('加载窗口数据失败');
        updateWindowSelect({});
    }
}

function updateWindowSelect(windowsData) {
    const select = document.getElementById('windowSelect');
    if (!select) return;

    select.innerHTML = '';

    if (!windowsData || Object.keys(windowsData).length === 0) {
        // 没有窗口数据时的默认选项
        const defaultWindows = [
            { id: 1, name: '默认窗口1' },
            { id: 2, name: '默认窗口2' },
            { id: 3, name: '默认窗口3' }
        ];
        defaultWindows.forEach(w => {
            const option = document.createElement('option');
            option.value = w.id;
            option.textContent = w.name;
            select.appendChild(option);
        });
        return;
    }

    for (const [id, info] of Object.entries(windowsData)) {
        const option = document.createElement('option');
        option.value = id;
        option.textContent = info.window_name || `窗口${id}`;
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
    const previousWindowId = currentWindowId;

    // 1. 先持久化新窗口ID
    localStorage.setItem('currentWindowId', windowId);
    currentWindowId = windowId;
    currentWindowInfo = windows[windowId];
    currentBusinessType = currentWindowInfo?.window_type || 'record';

    // 2. 更新UI
    if (!currentWindowInfo) {
        const select = document.getElementById('windowSelect');
        const selectedOption = select?.querySelector(`option[value="${windowId}"]`);
        const windowName = selectedOption?.textContent || `窗口${windowId}`;
        document.getElementById('windowName').textContent = windowName;
    } else {
        document.getElementById('windowName').textContent = currentWindowInfo.window_name;
    }
    document.getElementById('windowSelect').value = windowId;

    // 3. 清理旧资源
    if (ws) {
        ws.close();
        ws = null;
    }
    if (refreshTimer) {
        clearInterval(refreshTimer);
        refreshTimer = null;
    }

    // 4. 重置状态但不立即清空显示（保持旧数据直到新数据到来）
    currentCall = null;

    if (previousWindowId !== currentWindowId) {
        console.log(`切换到 ${currentWindowInfo?.window_name || '窗口' + windowId}`);
    }

    // 5. 先建立WebSocket连接，再加载数据
    initWebSocket();

    // 6. 立即加载一次数据
    await loadQueueStatus();

    // 7. 启动自动刷新
    startAutoRefresh();
}

// ==================== 当前叫号显示 ====================
function updateCurrentCallDisplay(queueNumber, patientName) {
    const numberElement = document.getElementById('callNumber');
    const patientElement = document.getElementById('patientName');

    if (numberElement && patientElement) {
        numberElement.textContent = queueNumber || '---';
        patientElement.textContent = patientName || '等待叫号';
    }
}

// ==================== 队列状态加载 ====================
async function loadQueueStatus() {
    try {
        const response = await fetch(`${API_BASE}/api/queue/status`);
        if (response.ok) {
            const data = await response.json();
            updateBusinessCards(data);
        }
    } catch (error) {
        showError('无法连接到服务器');
    }
}

function showError(message) {
    const container = document.getElementById('businessCards');
    if (container) {
        container.innerHTML = `
            <div class="empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"/>
                    <line x1="12" y1="8" x2="12" y2="12"/>
                    <line x1="12" y1="16" x2="12.01" y2="16"/>
                </svg>
                <span>${message}</span>
            </div>
        `;
    }
}

// ==================== 业务卡片更新 - 增量更新策略（无数据真空期） ====================
function updateBusinessCards(statusData) {
    const container = document.getElementById('businessCards');
    if (!container) return;

    // ✅ 关键：清空容器，移除“加载中...”等占位元素
    container.innerHTML = '';

    let businessList = [];

    console.log('当前窗口业务类型：', currentWindowInfo);

    if (currentWindowInfo?.window_type === 'general') {
        businessList = Object.keys(businessTypes);
    } else {
        businessList = currentWindowInfo.business_sort
            .split(',')
            .map(id => id.trim())
            .filter(id => businessTypes[id]);   // 过滤掉不存在的业务 ID
    }
    businessList = [...new Set(businessList)];

    if (businessList.length === 0) {
        container.innerHTML = '<div class="empty-state"><span>暂无可用业务</span></div>';
        return;
    }

    const businessId = businessList[0];
    const business = businessTypes[businessId];
    const businessType = business.type;
    console.log('处理业务：', businessId);
    console.log('当前窗口业务信息：', business);

    const waitingCount = businessList.reduce((sum, businessId) => {
        const count = statusData.business_status?.[businessId]?.waiting_count || 0;
        return sum + count;
    }, 0);
    console.log('总等待人数（累加）：', waitingCount);
    const iconSvg = getBusinessIcon(business.icon);

    // 创建业务卡片
    const card = document.createElement('div');
    card.className = 'business-card';
    card.id = `businessCard_${businessId}`;

    card.innerHTML = `
        <div class="business-header">
            <div class="business-name">
                <div class="icon" style="background: ${business.color}">${iconSvg}</div>
                ${business.name}
            </div>
            <div class="waiting-count">
                等待<strong id="waitingCount_${businessType}">${waitingCount}</strong>人
            </div>
        </div>
        <div class="queue-list" id="queueList_${businessType}">
            <div class="empty-state"><span>加载中...</span></div>
        </div>
        <button class="call-main-btn" onclick="window.callNext('${businessType}')">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
                <path d="M19.07 4.93a10 10 0 0 1 0 14.14"/>
                <path d="M15.54 8.46a5 5 0 0 1 0 7.07"/>
            </svg>
            叫下一个号
        </button>
    `;
    container.appendChild(card);

    // 加载该业务的排队列表
    loadQueueList(businessType);

    // 恢复当前叫号（如果有）
    if (statusData.current_calls && statusData.current_calls.length > 0) {
        const windowCall = statusData.current_calls.find(call => call.window_id === currentWindowId);
        if (windowCall) {
            currentCall = windowCall;
            updateCurrentCallDisplay(windowCall.queue_number, windowCall.patient_name || '患者');
        }
    }
}

function getBusinessIcon(type) {
    const icons = {
        pill: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.5 20.5L3.5 13.5C2.1 12.1 2.1 9.9 3.5 8.5L8.5 3.5C9.9 2.1 12.1 2.1 13.5 3.5L20.5 10.5C21.9 11.9 21.9 14.1 20.5 15.5L15.5 20.5C14.1 21.9 11.9 21.9 10.5 20.5Z"/><line x1="8.5" y1="8.5" x2="15.5" y2="15.5"/></svg>',
        file: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>',
        credit: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="1" y="4" width="22" height="16" rx="2" ry="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg>'
    };
    return icons[type] || icons.file;
}

async function loadQueueList(businessType) {
    try {
        const response = await fetch(`${API_BASE}/api/queue/list?window_id=${currentWindowId}&status=waiting`);
        if (response.ok) {
            const data = await response.json();
            console.log('获取排队列表成功:',businessType, data);
            updateQueueList(businessType, data.queues || []);
        } else {
            console.error('获取排队列表失败:',businessType, response);
        }
    } catch (error) {
        // 网络错误时保持现有数据，不清空
        console.error(`加载排队列表失败 (${businessType}):`, error);
    }
}

/**
 * 排队列表增量更新 - 修复患者姓名不显示问题
 */
function updateQueueList(businessType, queues) {
    const container = document.getElementById(`queueList_${businessType}`);
    if (!container) return;

    // 移除所有非 .queue-item 的子节点（如“加载中...”）
    const children = Array.from(container.children);
    for (const child of children) {
        if (!child.classList || !child.classList.contains('queue-item')) {
            child.remove();
        }
    }

    const currentQueues = queues || [];

    // 构建新数据 Map
    const newQueueMap = new Map();
    currentQueues.forEach(q => {
        newQueueMap.set(q.queue_number, q);
    });

    // 现有 DOM 元素 Map
    const existingItems = container.querySelectorAll('.queue-item');
    const existingMap = new Map();
    existingItems.forEach(item => {
        const queueNumber = item.dataset.queueNumber;
        existingMap.set(queueNumber, item);
    });

    // 删除不再存在的项
    existingItems.forEach(item => {
        const queueNumber = item.dataset.queueNumber;
        if (!newQueueMap.has(queueNumber)) {
            item.remove();
        }
    });

    // 添加或更新项
    const fragment = document.createDocumentFragment();
    currentQueues.forEach((queue) => {
        console.log('updateQueueList', queue);
        const existingItem = existingMap.get(queue.queue_number);
        const displayName = queue.patient_name && queue.patient_name.trim() ? queue.patient_name : '患者';
        const safePatientName = queue.patient_name || '';

        const isMedicalDone = businessType === 'medicine' && queue.medication_state == 1;
        console.log('==================', businessType, queue.medication_state, isMedicalDone);

        if (existingItem) {
            // ✅ 完全刷新内部 HTML，确保姓名、按钮参数都是最新的
            existingItem.innerHTML = `
                <div class="queue-info">
                    <span class="queue-number">${queue.queue_number}</span>
                    <span class="queue-name">${displayName}</span>
                    <span class="queue-biz-tag" style="background:#F59E0B;color:#fff;font-size:12px;padding:2px 6px;border-radius:4px;margin-left:8px;">${queue.business_name}</span>

                    ${
                      isMedicalDone ? `<span class="queue-state medical-done" > 已完成药品收集 </span>` : ``
                    }
                </div>
                <button class="call-btn" onclick="window.callSpecific('${queue.queue_number}', '${safePatientName}', '${businessType}')">呼叫</button>
            `;
            // 确保 item 在容器中的顺序（按原始顺序）
            if (existingItem.parentNode !== container) {
                container.appendChild(existingItem);
            }
        } else {
            // 新增项
            const item = document.createElement('div');
            item.className = 'queue-item';
            item.dataset.queueNumber = queue.queue_number;
            item.innerHTML = `
                <div class="queue-info">
                    <span class="queue-number">${queue.queue_number}</span>
                    <span class="queue-name">${displayName}</span>
                    <span class="queue-biz-tag" style="background:#F59E0B;color:#fff;font-size:12px;padding:2px 6px;border-radius:4px;margin-left:8px;">${queue.business_name}</span>
                    ${
                      isMedicalDone
                        ? `<span class="queue-state medical-done">
                               已完成药品收集
                           </span>`
                        : ``
                    }
                </div>
                <button class="call-btn" onclick="window.callSpecific('${queue.queue_number}', '${safePatientName}', '${businessType}')">呼叫</button>
            `;
            fragment.appendChild(item);
        }
    });

    if (fragment.children.length > 0) {
        container.appendChild(fragment);
    }

    // 最终没有排队患者时显示空状态
    if (currentQueues.length === 0 && container.querySelectorAll('.queue-item').length === 0) {
        container.innerHTML = '<div class="empty-state"><span>暂无等待患者</span></div>';
    }
}

// ==================== WebSocket ====================
function initWebSocket() {
    ws = new WebSocket(`${WS_URL}/ws/window/${currentWindowId}`);

    ws.onopen = () => {
        console.log('WebSocket 连接成功');
        ws.send('get_status');
    };

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            handleWebSocketMessage(data);
        } catch (e) {
            if (event.data === 'pong') return;
        }
    };

    ws.onerror = () => console.log('WebSocket 连接错误');

    ws.onclose = () => {
        console.log('WebSocket 连接断开，重连中...');
        setTimeout(() => initWebSocket(), 3000);
    };
}

function handleWebSocketMessage(data) {
    switch (data.type) {
        case 'init':
        case 'status':
            if (data.data && data.data.current_call) {
                currentCall = data.data.current_call;
                if (currentCall.window_id === currentWindowId) updateCurrentCallDisplay(currentCall.queue_number, currentCall.patient_name || '患者');
            } else {
                currentCall = null;
                updateCurrentCallDisplay('---', '等待叫号');
            }
            break;

        case 'call_success':
            currentCall = data.data;
            if (currentCall.window_id === currentWindowId) updateCurrentCallDisplay(data.data.queue_number, data.data.patient_name || '患者');
            console.log(`叫号成功：${data.data.queue_number}`);
            animateCallNumber();
            // 使用防抖刷新，避免频繁请求
            scheduleRefresh();
            break;

        case 'complete':
            console.log(`完成服务：${data.data.queue_number}`);
            if (currentCall && currentCall.queue_number === data.data.queue_number) {
                currentCall = null;
                updateCurrentCallDisplay('---', '等待叫号');
                setTimeout(() => {
                    if (currentBusinessType) callNext(currentBusinessType);
                }, 500);
            }
            // 使用防抖刷新
            scheduleRefresh();
            break;

        case 'skip':
            console.log(`过号：${data.data.queue_number}`);
            if (currentCall && currentCall.queue_number === data.data.queue_number) {
                currentCall = null;
                updateCurrentCallDisplay('---', '等待叫号');
                setTimeout(() => {
                    if (currentBusinessType) callNext(currentBusinessType);
                }, 500);
            }
            // 使用防抖刷新
            scheduleRefresh();
            break;

        case 'queue_update':
            // 使用防抖刷新
            scheduleRefresh();
            break;
    }
}

function animateCallNumber() {
    const callCard = document.querySelector('.current-call-card');
    if (callCard) {
        callCard.classList.add('calling-animation');
        setTimeout(() => callCard.classList.remove('calling-animation'), 1500);
    }
}

// ==================== 叫号功能 ====================
async function callNext(businessType) {
    // 互斥检查1：当前是否有正在服务的患者
    if (currentCall) {
        console.log('已有正在服务的患者，请先完成服务或过号');
        showToast('请先完成当前服务或过号');
        return;
    }

    // 互斥检查2：防止并发请求
    if (isCalling) {
        console.log('正在处理叫号请求，请稍后');
        return;
    }

    isCalling = true;
    console.log('正在呼叫下一个患者...');

    try {
        const response = await fetch(`${API_BASE}/api/call`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                call_type: 'next',
                window_id: currentWindowId,
                business_type: businessType
            })
        });

        const result = await response.json();

        if (result.success) {
            currentCall = result.queue;
            if (currentCall.window_id === currentWindowId) updateCurrentCallDisplay(result.queue.queue_number, result.queue.patient_name || '患者');
            playVoice(result.queue.queue_number, result.queue.patient_name);
            animateCallNumber();
            // 使用防抖刷新
            scheduleRefresh();
        } else {
            console.log(`叫号失败：${result.message || '没有等待的患者'}`);
            updateCurrentCallDisplay('无号', '');
            setTimeout(() => {
                if (document.getElementById('callNumber').textContent === '无号') {
                    updateCurrentCallDisplay('---', '等待叫号');
                }
            }, 1000);
        }
    } catch (error) {
        console.log('叫号失败：网络错误');
    } finally {
        isCalling = false;
    }
}

async function callSpecific(queueNumber, patientName, businessType) {
    // 互斥检查：已有正在服务的患者时，禁止重复呼叫（除非是同一个患者？）
    if (currentCall && currentCall.queue_number !== queueNumber) {
        console.log('已有正在服务的其他患者，请先完成当前服务');
        showToast('请先完成当前服务');
        return;
    }

    if (isCalling) {
        console.log('正在处理叫号请求，请稍后');
        return;
    }

    isCalling = true;
    updateCurrentCallDisplay(queueNumber, patientName || '');

    console.log(`重复呼叫：${queueNumber}  ${businessType}  `);

    try {
        const response = await fetch(`${API_BASE}/api/call`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                call_type: 'specific',
                window_id: currentWindowId,
                business_type: businessType,
                patient_name: patientName,
                queue_number: queueNumber
            })
        });

        const result = await response.json();

         if (result.success) {
            // 后端返回当前呼叫对象，更新 currentCall
            currentCall = result.queue || { queue_number: queueNumber, patient_name: patientName };
            updateCurrentCallDisplay(queueNumber, patientName || '患者');
            playVoice(queueNumber, patientName);
            animateCallNumber();
            console.log(`呼叫指定患者成功：${queueNumber}`);
        } else {
            console.log(`呼叫指定患者失败：${result.message}`);
            updateCurrentCallDisplay('---', '等待叫号');
        }
    } catch (error) {
        console.log('叫号失败：网络错误');
    } finally {
        isCalling = false;
    }
    scheduleRefresh();
}

// ==================== 服务完成 ====================
async function completeService() {
    if (!currentCall) {
        console.log('没有正在服务的患者');
        return;
    }
    if (isCalling) return; // 正在处理其他请求
    isCalling = true;
    try {
        const response = await fetch(`${API_BASE}/api/complete`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                queue_number: currentCall.queue_number,
                window_id: currentWindowId
            })
        });

        const result = await response.json();

        if (result.success) {
            console.log(`完成服务：${currentCall.queue_number}`);
            updateCurrentCallDisplay('---', '等待叫号');
            currentCall = null;
            // 使用防抖刷新
            scheduleRefresh();

            // 自动呼叫下一个，注意此时当前服务已结束，互斥锁需要释放后再 callNext
            setTimeout(() => {
                // 重新调用 callNext 前需确保 isCalling 已释放，并且当前没有新的 currentCall
                if (!currentCall && !isCalling) {
                    callNext(currentBusinessType);
                } else {
                    // 如果 isCalling 仍为 true，则稍后重试或放弃
                    console.log('自动叫号跳过：已有请求进行中或已有服务');
                }
            }, 500);
        }
    } catch (error) {
        console.log('完成服务失败：网络错误');
    } finally {
        isCalling = false;
    }
}

// ==================== 跳过/过号 ====================
async function skipCurrent() {
    if (!currentCall) {
        console.log('没有正在服务的患者');
        return;
    }
    if (isCalling) return;

    isCalling = true;
    try {
        const response = await fetch(`${API_BASE}/api/skip`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                queue_number: currentCall.queue_number,
                reason: '过号'
            })
        });

        const result = await response.json();

        if (result.success) {
            console.log(`过号：${currentCall.queue_number}`);
            updateCurrentCallDisplay('---', '等待叫号');
            currentCall = null;
            // 使用防抖刷新
            scheduleRefresh();

            setTimeout(() => {
                if (!currentCall && !isCalling) {
                    callNext(currentBusinessType);
                }
            }, 500);
        }
    } catch (error) {
        console.log('过号失败：网络错误');
    } finally {
        isCalling = false;
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

// ==================== 重复呼叫 ====================
async function recallCurrent() {
    if (!currentCall) {
        console.log('没有正在服务的患者');
        return;
    }

    playVoice(currentCall.queue_number, currentCall.patient_name);
    animateCallNumber();
    console.log(`重复呼叫：${currentCall.queue_number}`);
}

// ==================== 语音播报 ====================
function playVoice(queueNumber, patientName) {
    console.log(`播放语音：${queueNumber}`);
    if (!('speechSynthesis' in window)) return;

    // 取消当前播放
    window.speechSynthesis.cancel();
    setTimeout(() => { /* speak logic */ }, 50);

    const utterance = new SpeechSynthesisUtterance();
    utterance.text = patientName && patientName.trim()
        ? `请${queueNumber}号，${patientName}，到${currentWindowInfo?.window_name || '窗口'}办理业务`
        : `请${queueNumber}号，到${currentWindowInfo?.window_name || '窗口'}办理业务`;
    utterance.lang = 'zh-CN';
    utterance.rate = 0.9;
    utterance.volume = 1;

    console.log('播放语音：', utterance.text);

    // 关键修复：等待语音列表就绪
    const trySpeak = () => {
        const voices = window.speechSynthesis.getVoices();
        if (voices.length === 0) {
            console.log('等待语音列表就绪...');
            // 语音列表未加载，等待事件
            window.speechSynthesis.onvoiceschanged = trySpeak;
            return;
        }
        const zhVoice = voices.find(v => v.lang.startsWith('zh')) || voices[0];
        if (zhVoice) utterance.voice = zhVoice;
        console.log('使用语音：', zhVoice.name);
        window.speechSynthesis.speak(utterance);
    };
    trySpeak();
}

// ==================== 日志 ====================
function addLog(message) {
    const logList = document.getElementById('logList');
    if (logList) {
        const logItem = document.createElement('div');
        logItem.className = 'log-item';
        logItem.innerHTML = `
            <span class="log-time">${new Date().toLocaleTimeString()}</span>
            <span class="log-text">${message}</span>
        `;
        logList.insertBefore(logItem, logList.firstChild);

        while (logList.children.length > 50) {
            logList.removeChild(logList.lastChild);
        }
    }
}


// ==================== 防抖刷新 ====================
function scheduleRefresh() {
    // 清除之前的防抖定时器
    if (refreshDebounceTimer) {
        clearTimeout(refreshDebounceTimer);
    }
    // 设置新的防抖定时器，2秒后执行刷新
    refreshDebounceTimer = setTimeout(() => {
        loadQueueStatus();
    }, DEBOUNCE_DELAY);
}

// ==================== 自动刷新 ====================
function startAutoRefresh() {
    if (refreshTimer) clearInterval(refreshTimer);
    // 改为 15 秒刷新一次
    refreshTimer = setInterval(loadQueueStatus, REFRESH_INTERVAL);
}


// ==================== 导出全局函数 ====================
window.callNext = callNext;
window.callSpecific = callSpecific;
