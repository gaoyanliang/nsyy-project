/**
 * 医生窗口 - 排队叫号系统
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
let currentWindowInfo = null;
let ws = null;
let currentCall = null;
let currentCalls = [];        // 新增：当前窗口所有叫号中患者
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

    // 确保按钮可见性正确（即使窗口未切换）
    updatePharmacyButtonVisibility(currentWindowId);

    // ==================== 恢复并持久化"批量叫号数量" ====================
    const countSelect = document.getElementById('callCountSelect');
    if (countSelect) {
        // 默认值：HTML 里 selected 的项（一般是 1）
        const savedCount = localStorage.getItem('callCount');
        if (savedCount && countSelect.querySelector(`option[value="${savedCount}"]`)) {
            countSelect.value = savedCount;
        } else {
            // 没有存档时，保持 HTML 默认（× 1）
            countSelect.value = '1';
        }

        // 用户改变时立即保存
        countSelect.addEventListener('change', (e) => {
            localStorage.setItem('callCount', e.target.value);
        });
    }
    // =================================================================


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

    // Tab 切换事件
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            // 切换激活状态
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');

            // 切换面板
            const tab = this.dataset.tab;
            document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
            document.getElementById(tab + 'TabContent').classList.add('active');

            // 加载对应数据（如果尚未加载或需要刷新）
            if (tab === 'skipped') {
                loadSkippedList();
            } else if (tab === 'history') {
                loadHistory();
            }
        });
    });

    // 刷新按钮（刷新当前活动 Tab）
    document.getElementById('refreshTabBtn').addEventListener('click', function() {
        const activeTab = document.querySelector('.tab-btn.active');
        if (activeTab) {
            const tab = activeTab.dataset.tab;
            if (tab === 'skipped') {
                loadSkippedList();
            } else if (tab === 'history') {
                loadHistory();
            }
        }
    });
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
    currentCalls = [];   // 新增

    if (previousWindowId !== currentWindowId) {
        console.log(`切换到 ${currentWindowInfo?.window_name || '窗口' + windowId}`);
    }

    // 5. 先建立WebSocket连接，再加载数据
    initWebSocket();

    // 6. 立即加载一次数据
    await loadQueueStatus();

    // 7. 启动自动刷新
    startAutoRefresh();

    // 更新按钮可见性
    updatePharmacyButtonVisibility(windowId);

    // 切换窗口后 加载历史记录
    //await loadHistory();
    await loadSkippedList();
}

function updatePharmacyButtonVisibility(windowId) {
    const pharmacyLink = document.getElementById('pharmacyLink');
    if (!pharmacyLink) return;

    // 确保 windowId 为数字
    const id = Number(windowId);
    // 允许显示的窗口 ID 列表（窗口1和2）
    const allowedWindows = [1, 2, 3];
    if (allowedWindows.includes(id)) {
        pharmacyLink.style.display = 'inline-flex';  // 显示
    } else {
        pharmacyLink.style.display = 'none';         // 隐藏
    }
}

// ==================== 当前叫号显示 ====================

// 兼容单个：内部调用多参数版本
function updateCurrentCallDisplay(queueNumber, patientName) {
    if (queueNumber === '---' || !queueNumber) {
        updateCurrentCallsDisplay([]);
        return;
    }
    updateCurrentCallsDisplay([{ queue_number: queueNumber, patient_name: patientName }]);
}

// 多患者显示
function updateCurrentCallsDisplay(calls) {
    const numberElement = document.getElementById('callNumber');
    const patientElement = document.getElementById('patientName');
    if (!numberElement || !patientElement) return;

    if (!calls || calls.length === 0) {
        numberElement.textContent = '---';
        patientElement.textContent = '等待叫号';
        numberElement.classList.remove('multi');
        patientElement.classList.remove('multi');
        return;
    }

    const numbers = calls.map(c => c.queue_number).filter(Boolean);
    const names   = calls.map(c => (c.patient_name && c.patient_name.trim()) || '患者');

    numberElement.textContent = numbers.join('、');
    patientElement.textContent = names.join('、');

    if (calls.length > 1) {
        numberElement.classList.add('multi');
        patientElement.classList.add('multi');
    } else {
        numberElement.classList.remove('multi');
        patientElement.classList.remove('multi');
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

    `;
    container.appendChild(card);

    // 加载该业务的排队列表
    loadQueueList(businessType);

    // 恢复当前叫号（支持多个）
    if (statusData.current_calls && statusData.current_calls.length > 0) {
        const windowCalls = statusData.current_calls.filter(
            c => Number(c.window_id) === Number(currentWindowId)
        );
        if (windowCalls.length > 0) {
            currentCalls = windowCalls;
            currentCall = windowCalls[0];
            updateCurrentCallsDisplay(windowCalls);
        } else {
            currentCalls = [];
            currentCall = null;
            updateCurrentCallsDisplay([]);
        }
    } else {
        currentCalls = [];
        currentCall = null;
        updateCurrentCallsDisplay([]);
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
        //console.log('==================', businessType, queue.medication_state, isMedicalDone);

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

            `;
            // 放在  `; 里面
            //<button class="call-btn" onclick="window.callSpecific('${queue.queue_number}', '${safePatientName}', '${businessType}')">呼叫</button>
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

            `;
            // 放在  `; 里面
            // <button class="call-btn" onclick="window.callSpecific('${queue.queue_number}', '${safePatientName}', '${businessType}')">呼叫</button>
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

async function loadSkippedList() {
    try {
        const response = await fetch(`${API_BASE}/api/queue/overdue?business_type=${currentBusinessType}&window_id=${currentWindowId}`);
        if (response.ok) {
            const data = await response.json();
            updateSkippedList(data.list || []);
        }
    } catch (error) {
        console.error('加载过号列表失败:', error);
    }
}

function updateSkippedList(skippedItems) {
    const container = document.getElementById('skippedList');
    const countSpan = document.getElementById('skippedCount');  // 注意 ID 已改为 tab 内的 span
    if (!container) return;

    // 更新计数（同时更新按钮上的计数）
    if (countSpan) {
        //countSpan.textContent = skippedItems.length;
        countSpan.textContent = `共 ${skippedItems.length} 人`;
    }

    // countSpan.textContent = `共 ${skippedItems.length} 人`;
    container.innerHTML = '';

    if (skippedItems.length === 0) {
        container.innerHTML = '<div class="empty-state"><span>暂无过号患者</span></div>';
        return;
    }

    const fragment = document.createDocumentFragment();
    skippedItems.forEach(item => {
        const div = document.createElement('div');
        div.className = 'history-item';
        div.innerHTML = `
            <div class="history-info">
                <span class="history-number">${item.queue_number}</span>
                <span class="history-name">${item.patient_name || '患者'}</span>
                <span class="history-biz">${item.business_name}</span>
                <span class="history-status status-skipped">已过号</span>
            </div>
            <button class="btn btn-reactivate" onclick="window.wakeUpPatient('${item.patient_id}', '${item.queue_number}', '${item.business_type}')">
                重新激活
            </button>
        `;
        fragment.appendChild(div);
    });
    container.appendChild(fragment);
}

async function wakeUpPatient(patientId, queueNumber, businessType) {
    if (currentCall && currentCall.status === 'calling') {
        console.log('已有正在服务的患者，请先完成服务或过号');
        showToast('请先完成当前服务或过号');
        return;
    }
    try {
        const response = await fetch(`${API_BASE}/api/wakeup`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                business_type: businessType,
                queue_number: queueNumber,
                patient_id: patientId,
                window_id: currentWindowId
            })
        });

        const result = await response.json();
        if (result.success) {
            showToast(`唤醒成功，排队号：${result.queue_number}`);
            // 刷新当前队列和过号列表
            loadQueueStatus();
            loadSkippedList();
            // 可选：自动叫号？避免用户等待，可自动触发 callNext
        } else {
            showToast(`唤醒失败：${result.message}`);
        }
    } catch (error) {
        showToast('唤醒请求失败，请检查网络');
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
            console.log('收到状态消息:', data);

            const list1 = data.data.current_calls && data.data.current_calls.length > 0
                ? data.data.current_calls
                : (data.data.current_call ? [data.data.current_call] : []);

            if (list1.length > 0 && list1[0].window_id === currentWindowId) {
                currentCalls = list1;
                currentCall = list1[0];
                if (currentCall.window_id === currentWindowId) updateCurrentCallsDisplay(list1);
            }
            break;

        case 'call_success':
            const list = data.data_list && data.data_list.length > 0
                ? data.data_list
                : (data.data ? [data.data] : []);

            if (list.length > 0 && list[0].window_id === currentWindowId) {
                currentCalls = list;
                currentCall = list[0];
                if (currentCall.window_id === currentWindowId) updateCurrentCallsDisplay(list);
                console.log(`叫号成功：${list.map(q => q.queue_number).join('、')}`);
                animateCallNumber();
            }

            // 使用防抖刷新，避免频繁请求
            scheduleRefresh();
            break;

        case 'complete':
            console.log(`完成服务：${data.data.queue_number}`);
            if (currentCall && currentCall.queue_number === data.data.queue_number) {
                currentCall = null;
                updateCurrentCallDisplay('---', '等待叫号');
//                setTimeout(() => {
//                    if (currentBusinessType) callNext(currentBusinessType);
//                }, 500);
            }
            // 使用防抖刷新
            scheduleRefresh();
            break;

        case 'skip':
            console.log(`过号：${data.data.queue_number}`);
            if (currentCall && currentCall.queue_number === data.data.queue_number) {
                currentCall = null;
                updateCurrentCallDisplay('---', '等待叫号');
//                setTimeout(() => {
//                    if (currentBusinessType) callNext(currentBusinessType);
//                }, 500);
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
    if (currentCall && currentCall.status === 'calling') {
        console.log('已有正在服务的患者，请先完成服务或过号');
        showToast('请先完成当前服务或过号');
        return;
    }

    // 互斥检查2：防止并发请求
    if (isCalling) {
        console.log('正在处理叫号请求，请稍后');
        return;
    }

    // 读取叫号数量
    const countSelect = document.getElementById('callCountSelect');
    const count = countSelect ? Math.max(1, parseInt(countSelect.value) || 1) : 1;

    isCalling = true;
    console.log('正在呼叫下一个患者...');

    try {
        const response = await fetch(`${API_BASE}/api/call`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                call_type: 'next',
                window_id: currentWindowId,
                business_type: businessType,
                business_id: '',
                patient_name: '',
                queue_number: '',
                count: count      // 新增
            })
        });

        const result = await response.json();

        if (result.success) {
            const queues = result.queues
                ? result.queues
                : Array.isArray(result.queue)
                    ? result.queue
                    : result.queue
                        ? [result.queue]
                        : [];

            if (queues.length === 0) {
                updateCurrentCallsDisplay([]);
                return;
            }
            currentCalls = queues;
            currentCall = queues[0];
            if (currentCall.window_id === currentWindowId) updateCurrentCallsDisplay(queues);

            // 后端返回当前呼叫对象，更新 currentCall
//            currentCall = result.queue;
//            if (currentCall.window_id === currentWindowId) updateCurrentCallDisplay(result.queue.queue_number, result.queue.patient_name || '患者');
            playVoiceMulti(queues);
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
                business_id: '',
                patient_name: patientName,
                queue_number: queueNumber
            })
        });

        const result = await response.json();

         if (result.success) {
            const queues = result.queues
                ? result.queues
                : Array.isArray(result.queue)
                    ? result.queue
                    : result.queue
                        ? [result.queue]
                        : [];

            if (queues.length === 0) {
                updateCurrentCallsDisplay([]);
                return;
            }

            currentCall = queues[0];
            if (currentCall.window_id === currentWindowId) updateCurrentCallsDisplay(queues);
            playVoiceMulti(queues);
            animateCallNumber();
            // 使用防抖刷新
            scheduleRefresh();
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
    if (!currentCall || currentCall.status !== 'calling') {
        // 若 currentCalls 有数据，允许直接完成
        if (currentCalls.length === 0) {
            console.log('没有正在服务的患者');
            showToast('没有正在服务的患者');
            return;
        }
    }
    if (isCalling) return;
    isCalling = true;

    const target = currentCall || currentCalls[0];
    if (!target) {
        console.log('没有可完成的患者');
        isCalling = false;
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/complete`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                status: 0,
                queue_number: target.queue_number,
                window_id: currentWindowId
            })
        });

        const result = await response.json();

        if (result.success) {
            console.log(`完成服务：${target.queue_number}`);

            // 从列表移除已完成患者
            currentCalls = currentCalls.filter(c => c.queue_number !== target.queue_number);

            if (currentCalls.length > 0) {
                currentCall = currentCalls[0];
                updateCurrentCallsDisplay(currentCalls);
            } else {
                currentCall = null;
                updateCurrentCallsDisplay([]);

                // 无剩余，自动叫下一个
//                setTimeout(() => {
//                    // 自动呼叫下一个，注意此时当前服务已结束，互斥锁需要释放后再 callNext
//                    if (currentCalls.length === 0 && !isCalling) {
//                        callNext(currentBusinessType);
//                    } else {
//                        // 如果 isCalling 仍为 true，则稍后重试或放弃
//                        console.log('自动叫号跳过：已有请求进行中或已有服务');
//                    }
//                }, 500);
            }

            // 使用防抖刷新
            scheduleRefresh();
            loadHistory(); // 新增
        }   else {
            console.log('完成服务失败：', result.message || '接口返回失败');
            showToast(result.message || '完成服务失败');
        }
    } catch (error) {
        // ✅ 打印真实错误，别再一律叫"网络错误"
        console.error('完成服务异常:', error);
        showToast('完成服务异常，请查看控制台');
    } finally {
        isCalling = false;
    }
}

// ==================== 跳过/过号 ====================
async function skipCurrent() {
    if (!currentCall && currentCalls.length === 0) {
        showToast('没有正在服务的患者');
        return;
    }
    if (isCalling) return;
    isCalling = true;

    const target = currentCall || currentCalls[0];
    try {
        const response = await fetch(`${API_BASE}/api/skip`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                queue_number: target.queue_number,
                reason: '过号'
            })
        });

        const result = await response.json();

        if (result.success) {
            console.log(`过号：${target.queue_number}`);
            currentCalls = currentCalls.filter(c => c.queue_number !== target.queue_number);

            if (currentCalls.length > 0) {
                currentCall = currentCalls[0];
                updateCurrentCallsDisplay(currentCalls);
            } else {
                currentCall = null;
                updateCurrentCallsDisplay([]);

//                setTimeout(() => {
//                    if (currentCalls.length === 0 && !isCalling) {
//                        callNext(currentBusinessType);
//                    }
//                }, 500);
            }
            scheduleRefresh();
            loadSkippedList();
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
    if (currentCalls.length === 0 || currentCall.status !== 'calling') {
        console.log('没有正在服务的患者');
        showToast('没有正在服务的患者');
        return;
    }
    // 重呼时把所有已叫号的患者再拼一次
    await playVoiceMulti(currentCalls);
    animateCallNumber();
    console.log(`重复呼叫：${currentCalls.map(q => q.queue_number).join('、')}`);
}

// ==================== 语音播报 ====================
function playVoice1(queueNumber, patientName) {
    console.log(`播放语音：${queueNumber}`);
    if (!('speechSynthesis' in window)) return;

    // 取消当前播放
    window.speechSynthesis.cancel();
    setTimeout(() => { /* speak logic */ }, 50);

    const utterance = new SpeechSynthesisUtterance();
    utterance.text = patientName && patientName.trim()
        ? `请 ${patientName}，到${currentWindowInfo?.window_name || '窗口'}办理业务`
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

async function playVoice(queueNumber, patientName) {
    console.log('播放语音：playVoice 11111111111111111111111')
    console.log(`播放语音：${queueNumber}`);
    try {
        const response = await fetch(`${API_BASE}/api/tts_call`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                call_type: 'tts_call',
                business_type: '',
                business_id: '',
                queue_number: queueNumber,
                patient_name: patientName,
                window_id: currentWindowId
            })
        });

        const result = await response.json();
        if (result.success) {
            showToast('呼叫成功');
        } else {
           console.log('呼叫识别失败：', result);
           showToast('呼叫失败，请稍后重试');
        }
    } catch (error) {
        console.log('呼叫识别失败：', error);
        showToast('呼叫失败，请稍后重试');
    }
}

async function playVoiceMulti(queues) {
    console.log('播放语音：playVoiceMulti 22222222222222222222')
    if (!queues || queues.length === 0) return;
    const names = queues
        .map(q => (q.patient_name || '').trim())
        .filter(Boolean);

    const numbers = queues
        .map(q => (q.queue_number || '').trim())
        .filter(Boolean);

    // 让窗口大屏拼接播报：把合并后的人名作为 patient_name 传入
    const combinedName = names.length > 0 ? names.join('、') : '';
    const combineNumber = numbers.length > 0 ? numbers.join('、') : '';

    try {
        const response = await fetch(`${API_BASE}/api/tts_call`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                call_type: 'tts_call',
                business_type: '',
                business_id: '',
                queue_number: combineNumber,
                patient_name: combinedName,      // 大屏会拼接成 "请 张三、李四、王五，到X窗口办理业务"
                window_id: currentWindowId
            })
        });

        const result = await response.json();
        if (result.success) {
            showToast(`呼叫成功（${queues.length} 人）`);
        } else {
            showToast('呼叫失败，请稍后重试');
        }
    } catch (error) {
        console.log('呼叫识别失败：', error);
        showToast('呼叫失败，请稍后重试');
    }
}

// ==================== 历史记录加载 ====================
async function loadHistory() {
    try {
        const response = await fetch(`${API_BASE}/api/queue/history/${currentWindowId}`);
        if (response.ok) {
            const data = await response.json();
            updateHistoryList(data.history || []);
        } else {
            console.warn('加载历史记录失败，使用空数据');
            updateHistoryList([]);
        }
    } catch (error) {
        console.error('历史记录加载异常:', error);
        updateHistoryList([]);
    }
}

function updateHistoryList(historyItems) {
    const container = document.getElementById('historyList');
    const countSpan = document.getElementById('historyCount');
    if (!container) return;

    // 更新计数
    if (countSpan) {
        countSpan.textContent = `共 ${historyItems.length} 人`;
    }

    // 清空容器，保留空状态样式（用于无数据时）
    container.innerHTML = '';

    if (!historyItems || historyItems.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="40" height="40">
                    <circle cx="12" cy="12" r="10"/>
                    <line x1="12" y1="8" x2="12" y2="12"/>
                    <line x1="12" y1="16" x2="12.01" y2="16"/>
                </svg>
                <span>暂无已服务患者</span>
            </div>
        `;
        return;
    }

    // 按服务时间倒序排列（最新的在前）
    const sorted = [...historyItems].sort((a, b) => {
        return new Date(b.service_time) - new Date(a.service_time);
    });

    const fragment = document.createDocumentFragment();
    sorted.forEach(item => {
        const div = document.createElement('div');
        div.className = 'history-item'; // 自定义样式，稍后在 CSS 中补充

        const statusText = item.status === 'completed' ? '已完成' : '已过号';
        const statusClass = item.status === 'completed' ? 'status-completed' : 'status-skipped';

        div.innerHTML = `
            <div class="history-info">
                <span class="history-number">${item.queue_number}</span>
                <span class="history-name">${item.patient_name || '患者'}</span>
                <span class="history-biz">${item.business_name || '通用业务'}</span>
                <span class="history-status ${statusClass}">${statusText}</span>
            </div>
            <span class="history-time">${item.service_time}</span>
        `;
        fragment.appendChild(div);
    });
    container.appendChild(fragment);
}

// 辅助：格式化时间
function formatTime(dateString) {
    if (!dateString) return '--:--';
    const date = new Date(dateString);
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
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
window.loadHistory = loadHistory;
