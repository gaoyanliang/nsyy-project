/**
 * 门诊取药管理 - JavaScript
 * 简洁大气 干净美观
 *
 * 功能：待取药列表、已取药列表、药品详情展开显示、取药完成、WebSocket实时更新
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
        wsUrl: `ws://${host}:${port}/mz/ws/pharmacy`
    };

}

// 根据当前环境生成配置
const config = getApiConfig();
const API_BASE = config.apiBase;
const WS_URL = config.wsUrl;


// business id = 1 为取药业务
const business_id = 1;

// 状态管理
let currentTab = 'pending'; // pending | completed
let selectedPatientId = null; // 当前选中的患者队列号
let pendingPatients = [];    // 待取药患者列表
let completedPatients = [];  // 已取药患者列表
let medicinesCache = new Map(); // 药品缓存
let ws = null;
let wsReconnectTimer = null;
let cachedPatientsData = []; // 缓存患者完整数据（包含药品）
let voiceAlertEnabled = true; // 语音提醒开关状态
let lastPendingCount = 0; // 上一次待发药患者数量（用于检测新增）

// ==================== 初始化 ====================
document.addEventListener('DOMContentLoaded', () => {
    init();
});

// ==================== 初始化函数 ====================
async function init() {
    // 启动时钟
    startClock();

    // Tab切换事件
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.dataset.tab;
            switchTab(tab);
        });
    });

    // 初始化语音开关
    initVoiceSwitch();

    // 连接WebSocket
    connectWebSocket();

    // 加载数据
    await loadAllData();

    // 定时刷新（备用）
    setInterval(loadAllData, 20*1000);
}

// ==================== WebSocket ====================
function connectWebSocket() {
    try {
        ws = new WebSocket(WS_URL);

        ws.onopen = () => {
            updateWsStatus(true);
            console.log('WebSocket connected');
            // 订阅取药相关事件
            sendWsMessage({ type: 'subscribe', channel: 'pharmacy' });
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                handleWsMessage(data);
            } catch (e) {
                console.error('WebSocket message parse error:', e);
            }
        };

        ws.onclose = () => {
            updateWsStatus(false);
            console.log('WebSocket disconnected, reconnecting...');
            // 重连
            wsReconnectTimer = setTimeout(connectWebSocket, 5000);
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            updateWsStatus(false);
        };
    } catch (error) {
        console.error('WebSocket connection error:', error);
        updateWsStatus(false);
        wsReconnectTimer = setTimeout(connectWebSocket, 5000);
    }
}

function sendWsMessage(data) {
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(data));
    }
}

function handleWsMessage(data) {
    switch (data.type) {
        case 'init':
            // 取药队列更新
            loadAllData();
            break;
        case 'pharmacy_update':
            // 取药队列更新
            loadAllData();
            break;
        case 'queue_update':
            // 通用队列更新
            loadAllData();
            break;
    }
}

function updateWsStatus(connected) {
    const statusEl = document.getElementById('wsStatus');
    const textEl = document.getElementById('wsStatusText');
    if (statusEl && textEl) {
        if (connected) {
            statusEl.classList.remove('disconnected');
            textEl.textContent = '系统正常';
        } else {
            statusEl.classList.add('disconnected');
            textEl.textContent = '连接断开';
        }
    }
}

// ==================== 时钟 ====================
function startClock() {
    updateClock();
    setInterval(updateClock, 1000);
}

function updateClock() {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const seconds = String(now.getSeconds()).padStart(2, '0');

    const dateEl = document.getElementById('currentDate');
    const timeEl = document.getElementById('currentTime');
    if (dateEl) dateEl.textContent = `${year}-${month}-${day}`;
    if (timeEl) timeEl.textContent = `${hours}:${minutes}:${seconds}`;
}

// ==================== 加载数据 ====================
async function loadAllData() {
    await Promise.all([
        loadPendingPatients(),
        loadCompletedPatients()
    ]);
}

async function loadPendingPatients() {
    try {
        const response = await fetch(`${API_BASE}/api/queue/list?business_id=${business_id}&status=waiting`);
        if (response.ok) {
            const data = await response.json();
            const oldPendingCount = pendingPatients.filter(p => {
                const state = parseInt(p.medication_state);
                return state === 0 || state === 1;
            }).length;

            pendingPatients = data.queues || [];
            console.log('获取待取药列表成功:', data);
            updatePatientCount('pendingCount', pendingPatients.length);
            renderPatientList();

            // 检查是否有新增的待发药患者
            const newPendingCount = pendingPatients.filter(p => {
                const state = parseInt(p.medication_state);
                return state === 0 || state === 1;
            }).length;

            // 如果开关开启且有待发药患者，触发语音播报
            // ✅ 只有数量"增加"时才播报（避免每 20 秒刷屏）
            if (voiceAlertEnabled && newPendingCount > lastPendingCount) {
                const added = newPendingCount - lastPendingCount;
                setTimeout(() => {
                    announcePendingPatients(added);
                }, 500);
            }

            lastPendingCount = newPendingCount;
        }
    } catch (error) {
        console.error('加载待取药列表失败:', error);
    }
}

async function loadCompletedPatients() {
    try {
        const response = await fetch(`${API_BASE}/api/queue/list?business_id=${business_id}&status=completed`);
        if (response.ok) {
            const data = await response.json();
            completedPatients = data.queues || [];
            console.log('获取已取药列表成功:', data);
            completedPatients = completedPatients.slice(0, 20);
            updatePatientCount('completedCount', completedPatients.length);
            if (currentTab === 'completed') {
                renderPatientList();
            }
        }
    } catch (error) {
        console.error('加载已取药列表失败:', error);
    }
}

function updatePatientCount(elementId, count) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = count;
    }
}

// ==================== Tab切换 ====================
function switchTab(tab) {
    if (currentTab === tab) return;

    currentTab = tab;

    // 更新Tab样式
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tab);
    });

    // 更新标题
    const listTitle = document.getElementById('listTitle');
    if (listTitle) {
        listTitle.textContent = tab === 'pending' ? '待取药患者' : '已取药患者';
    }

    // 清除选中状态
    selectedPatientId = null;

    // 渲染列表
    renderPatientList();
}

// ==================== 渲染患者列表（展开式） ====================
function renderPatientList() {
    const container = document.getElementById('patientList');
    const patients = currentTab === 'pending' ? pendingPatients : completedPatients;

    if (patients.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"/>
                    <line x1="12" y1="8" x2="12" y2="12"/>
                    <line x1="12" y1="16" x2="12.01" y2="16"/>
                </svg>
                <span>${currentTab === 'pending' ? '暂无待取药患者' : '暂无已取药记录'}</span>
            </div>
        `;
        cachedPatientsData = [];   // ✅ 清空缓存
        return;
    }

    // 保存完整数据用于后续查询
    cachedPatientsData = patients;

    container.innerHTML = '';
    patients.forEach((patient, index) => {
        const item = createPatientCard(patient, index);
        container.appendChild(item);
    });

    // 如果当前有选中的患者，恢复展开状态
    if (selectedPatientId) {
        const patient = patients.find(p => p.queue_number === selectedPatientId);
        if (patient) {
            const medicinesEl = document.getElementById(`medicines-${selectedPatientId}`);
            if (medicinesEl) {
                if (medicinesCache.has(selectedPatientId)) {
                    medicinesEl.innerHTML = medicinesCache.get(selectedPatientId);
                } else {
                    // 缓存不存在时重新加载（比如刚刷新完成，缓存被清除）
                    const name = patient.patient_name || '患者';
                    const idCard = patient.patient_id || '';
                    loadMedicines(patient.medication_state, selectedPatientId, idCard, name);
                }
            }
        } else {
            // 如果选中的患者不在当前列表中（比如已移到已完成），清除选中状态
            selectedPatientId = null;
        }
    }
}

function createPatientCard(patient, index) {
    const item = document.createElement('div');
    item.className = `patient-item${currentTab === 'completed' ? ' completed' : ''}${selectedPatientId === patient.queue_number ? ' selected' : ''}`;
    item.dataset.queueNumber = patient.queue_number;
    item.style.animationDelay = `${index * 0.05}s`;

    console.log("当前患者； ", patient);
    const fullIdCard = patient.patient_id || '';
    const displayId = formatIdCard(fullIdCard);
    const name = patient.patient_name || '患者';
    const idCard = patient.patient_id || '身份证未知';
    const nameInitial = name.charAt(0);
    const stateInfo = getStateInfo(patient.medication_state);

    item.innerHTML = `
        <div class="patient-header" onclick="togglePatient('${patient.medication_state}', '${patient.queue_number}', '${patient.patient_id}', '${name.replace(/'/g, "\\'")}')">
            <div class="patient-info">
                <div class="patient-avatar">${nameInitial}</div>
                <div class="patient-details">
                    <div class="patient-name"
                         onclick="copyText('${name.replace(/'/g, "\\'")}'); event.stopPropagation();"
                         title="点击复制姓名">
                        ${name} <span class="copy-hint">📋</span>
                    </div>
                    <div class="patient-id"
                         onclick="copyText('${fullIdCard.replace(/'/g, "\\'")}'); event.stopPropagation();"
                         title="点击复制完整身份证号">
                        ${displayId} <span class="copy-hint">📋</span>
                    </div>
                </div>
            </div>
            <div class="patient-meta">
                <span class="patient-state ${stateInfo.className}">
                    ${stateInfo.icon}
                    ${stateInfo.text}
                </span>
                <div class="patient-time">${formatTime(patient.create_time)}</div>
                <svg class="expand-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="6 9 12 15 18 9"/>
                </svg>
            </div>
        </div>
        <div class="patient-medicines" id="medicines-${patient.queue_number}">
            <!-- 药品详情将在这里动态加载 -->
        </div>
    `;

    return item;
}

// 获取状态对应的文本、CSS类名和图标
function getStateInfo(medicationState) {
    const state = parseInt(medicationState);
    switch (state) {
        case 0:
            return {
                text: '待发药',
                className: 'waiting',
                // 时钟 → 等待药师处理
                icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                          <circle cx="12" cy="12" r="10"/>
                          <polyline points="12 6 12 12 16 14"/>
                       </svg>`
            };
        case 1:
            return {
                text: '药品收集中',
                className: 'in-progress',
                // 药瓶 / 配药中（比 loading 更符合业务）
                icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                          <path d="M8 2h8l1 3H7z"/>
                          <path d="M7 5v15a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2V5"/>
                          <path d="M12 11v4"/>
                          <path d="M10 13h4"/>
                       </svg>`
            };
        case 2:
            return {
                text: '待患者领取',
                className: 'completed',
                // 双手递接 / 等待患者（不用对勾）
                icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                          <path d="M4 17v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"/>
                          <path d="M12 12v7"/>
                          <path d="M7 8l5-5 5 5"/>
                          <path d="M12 3v9"/>
                       </svg>`
            };
        case 3:
            return {
                text: '患者已领取',
                className: 'completed',
                // 成功对勾（唯一终点状态）
                icon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                          <polyline points="22 4 12 14.01 9 11.01"/>
                       </svg>`
            };
        default:
            return {
                text: '未知状态',
                className: '',
                icon: ''
            };
    }
}

// ==================== 展开/收起患者药品详情 ====================
async function togglePatient(medication_state, queueNumber, idCard, patientName) {
    const isCurrentlySelected = selectedPatientId === queueNumber;

    if (isCurrentlySelected) {
        // 收起
        selectedPatientId = null;
        const medicinesEl = document.getElementById(`medicines-${queueNumber}`);
        if (medicinesEl) {
            medicinesEl.innerHTML = '';
        }
        document.querySelectorAll('.patient-item').forEach(item => {
            item.classList.remove('selected');
        });
        return;
    }

    // 选择新的患者
    selectedPatientId = queueNumber;

    // 更新选中样式
    document.querySelectorAll('.patient-item').forEach(item => {
        item.classList.toggle('selected', item.dataset.queueNumber === queueNumber);
    });

    // 加载药品详情
    const medicinesEl = document.getElementById(`medicines-${queueNumber}`);
    if (!medicinesEl) return;

    // 检查缓存（缓存的是 HTML 字符串）
    if (medicinesCache.has(queueNumber)) {
        medicinesEl.innerHTML = medicinesCache.get(queueNumber);
        return;
    }

    // 显示加载状态
    medicinesEl.innerHTML = `
        <div class="medicines-loading">
            <div class="spinner"></div>
            <span>加载药品清单...</span>
        </div>
    `;

    // 加载药品（会异步填充并缓存 HTML）
    await loadMedicines(medication_state, queueNumber, idCard, patientName);
}

// ==================== 加载药品清单 ====================
async function loadMedicines(medication_state, queueNumber, idCard, patientName) {
    const medicinesEl = document.getElementById(`medicines-${queueNumber}`);
    if (!medicinesEl) return;

    try {
        const response = await fetch(`${API_BASE}/api/patient/${idCard}/medicines`);
        if (response.ok) {
            const data = await response.json();
            const medicines = data.medicines || [];

            // 生成 HTML
            const html = renderMedicinesHTML(medication_state, patientName, medicines, queueNumber);
            medicinesEl.innerHTML = html;

            // 缓存 HTML 字符串（不再缓存数据数组）
            medicinesCache.set(queueNumber, html);
        } else {
            throw new Error('请求失败');
        }
    } catch (error) {
        console.error('加载药品清单失败:', error);
        medicinesEl.innerHTML = `
            <div class="no-medicines">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"/>
                    <line x1="15" y1="9" x2="9" y2="15"/>
                    <line x1="9" y1="9" x2="15" y2="15"/>
                </svg>
                <span>加载失败，请重试</span>
            </div>
        `;
    }
}

// ==================== 渲染药品列表HTML ====================
function renderMedicinesHTML(medication_state, patientName, medicines, queueNumber) {
    if (!medicines || medicines.length === 0) {
        return `
            <div class="no-medicines">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M10.5 20.5L3.5 13.5C2.1 12.1 2.1 9.9 3.5 8.5L8.5 3.5C9.9 2.1 12.1 2.1 13.5 3.5L20.5 10.5C21.9 11.9 21.9 14.1 20.5 15.5L15.5 20.5C14.1 21.9 11.9 21.9 10.5 20.5Z"/>
                    <line x1="8.5" y1="8.5" x2="15.5" y2="15.5"/>
                </svg>
                <span>该患者暂无药品记录</span>
            </div>
        `;
    }

    const paidCount = medicines.filter(m => m.status === 'paid' || m.payment_status === 'paid').length;
    const unpaidCount = medicines.length - paidCount;

    let html = `
        <div class="medicine-stats">
            <div class="stat-card paid">
                <div class="stat-value">${paidCount}</div>
                <div class="stat-label">已缴费</div>
            </div>
            <div class="stat-card unpaid">
                <div class="stat-value">${unpaidCount}</div>
                <div class="stat-label">未缴费</div>
            </div>
            <div class="stat-card total">
                <div class="stat-value">${medicines.length}</div>
                <div class="stat-label">药品总数</div>
            </div>
        </div>
        <div class="medicine-list">
    `;

    medicines.forEach((medicine, index) => {
        const isPaid = medicine.zt === 1;
        const statusClass = isPaid ? 'paid' : 'unpaid';
        const statusText = isPaid ? '已缴费' : '未缴费';

        const isTake = medicine.fayaobz === 1;
        const statusClassT = isTake ? 'paid' : 'unpaid';
        const statusTextT = isTake ? '已取药' : '未取药';

        const medicineName = medicine.yizhumc || '药品';
        const medicineDept = medicine.kaidanksmc || '';
        const medicineDoctor = medicine.kaidanysxm || '';

        html += `
            <div class="medicine-item" style="animation-delay: ${index * 0.05}s;">
                <div class="medicine-info">
                    <div class="medicine-name">${medicineName}</div>
                    <div class="medicine-spec">开药科室: ${medicineDept}</div>
                    <div class="medicine-spec">开药医生: ${medicineDoctor}</div>
                </div>

                <div class="status-group">
                    <span class="medicine-status ${statusClass}">${statusText}</span>
                    <span class="medicine-status ${statusClassT}">${statusTextT}</span>
                </div>
            </div>
        `;
    });

    html += '</div>';

    console.log("打印状态:", medication_state)

    // 仅在待取药tab显示确认取药按钮
    if (currentTab === 'pending') {
        const stateNum = parseInt(medication_state);
        let btnClass, btnText, disabled, onClick;


        if (stateNum === 0) {
            btnClass = 'completed-btn';
            btnText = '待发药';
            disabled = true;
            onClick = '';
        } else if (stateNum === 1) {
            btnClass = 'complete-btn';
            btnText = '药品收集完成';
            disabled = false;
            onClick = `completePickup('${queueNumber}', 2)`;
        } else if (stateNum === 2) {
            btnClass = 'complete-btn';
            btnText = '患者完成取药';
            disabled = false;
            onClick = `completePickup('${queueNumber}', 3)`;
        } else {
             btnClass = 'completed-btn';
            btnText = '患者已取药';
            disabled = true;
            onClick = '';
        }

        html += `
            <div class="action-buttons">
                <button class="${btnClass}" onclick="${onClick}" ${disabled ? 'disabled' : ''}>
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                        <polyline points="22 4 12 14.01 9 11.01"/>
                    </svg>
                    ${btnText}
                </button>
            </div>
        `;
    }
    return html;
}

// ==================== 取药完成 ====================
async function completePickup(queueNumber, status) {
    if (!queueNumber) {
        showToast('请先选择患者', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/medicine/complete`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                queue_number: queueNumber,
                window_id: 0,
                status: status
            })
        });

        if (response.ok) {
            showToast('成功🏅！', 'success');

            // 清除缓存
            medicinesCache.delete(queueNumber);

            // 重新加载数据
            await loadAllData();
        } else {
            throw new Error('请求失败');
        }
    } catch (error) {
        console.error('完成取药失败:', error);
        showToast('操作失败，请重试', 'error');
    }
}

// ==================== 工具函数 ====================
function formatTime(timeStr) {
    if (!timeStr) return '';
    const date = new Date(timeStr);
    const now = new Date();
    const diff = Math.floor((now - date) / 1000 / 60);

    if (diff < 1) return '刚刚';
    if (diff < 60) return `${diff}分钟前`;
    if (diff < 1440) return `${Math.floor(diff / 60)}小时前`;
    return `${Math.floor(diff / 1440)}天前`;
}

function formatIdCard(idCard) {
    if (!idCard || idCard.length < 8) return idCard;
    return idCard.substring(0, 4) + '****' + idCard.substring(idCard.length - 4);
}

function showToast(message, type = 'success') {
    const existingToast = document.querySelector('.success-toast');
    if (existingToast) existingToast.remove();

    const toast = document.createElement('div');
    toast.className = `success-toast${type === 'error' ? ' error' : ''}`;
    toast.innerHTML = `
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            ${type === 'success'
                ? '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>'
                : '<circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>'
            }
        </svg>
        <span>${message}</span>
    `;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease-out reverse';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// 弹窗功能
function showModal(content) {
    const modal = document.getElementById('modalOverlay');
    const modalBody = document.getElementById('modalBody');
    modalBody.innerHTML = content;
    modal.classList.add('show');
}

function closeModal() {
    const modal = document.getElementById('modalOverlay');
    modal.classList.remove('show');
}


// ==================== 复制功能 ====================
function copyText(text) {
    if (!text) {
        showToast('无内容可复制', 'error');
        return;
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(() => {
            showToast('已复制: ' + text, 'success');
        }).catch(() => {
            fallbackCopy(text);
        });
    } else {
        fallbackCopy(text);
    }
}

function fallbackCopy(text) {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    document.body.appendChild(textarea);
    textarea.select();
    try {
        document.execCommand('copy');
        showToast('已复制: ' + text, 'success');
    } catch (e) {
        showToast('复制失败', 'error');
    }
    document.body.removeChild(textarea);
}

// 点击遮罩关闭弹窗
document.getElementById('modalOverlay')?.addEventListener('click', (e) => {
    if (e.target.id === 'modalOverlay') {
        closeModal();
    }
});

// 页面关闭前清理
window.addEventListener('beforeunload', () => {
    if (wsReconnectTimer) {
        clearTimeout(wsReconnectTimer);
    }
    if (ws) {
        ws.close();
    }
});

// ==================== 语音提醒功能 ====================

// 初始化语音开关
function initVoiceSwitch() {
    const voiceSwitch = document.getElementById('voiceSwitch');
    if (voiceSwitch) {
        // 从本地存储加载状态
        const savedState = localStorage.getItem('voiceAlertEnabled');
        if (savedState !== null) {
            voiceAlertEnabled = savedState === 'true';
            voiceSwitch.checked = voiceAlertEnabled;
        }

        // 监听开关变化
        voiceSwitch.addEventListener('change', (e) => {
            voiceAlertEnabled = e.target.checked;
            localStorage.setItem('voiceAlertEnabled', voiceAlertEnabled);

            // 如果开启且有待发药患者，立即播报
            if (voiceAlertEnabled && pendingPatients.length > 0) {
                announcePendingPatients();
            }
        });
    }
}

// 语音播报待发药患者
function announcePendingPatients(added = 0) {
    if (!voiceAlertEnabled) return;
    if (!('speechSynthesis' in window)) return;

    speechSynthesis.cancel();

    // 有新增时播报"有 N 位新增待发药"
    // 首次进入页面（added === 总数）时，播报"有 N 位患者待发药"
    const total = pendingPatients.filter(p => {
        const state = parseInt(p.medication_state);
        return state === 0 || state === 1;
    }).length;

    const msg = added > 0 && added < total
        ? `您好，新增${added}位患者待发药，请尽快安排`
        : `您好，有${total}位患者待发药，请尽快安排`;

    speakText(msg);
}

// 执行语音播报
function speakText(text) {
    if (!('speechSynthesis' in window)) {
        console.log('浏览器不支持语音合成');
        return;
    }

    // 取消之前的播报
    speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);

    // 设置语音参数
    utterance.lang = 'zh-CN'; // 中文
    utterance.rate = 1.2;      // 语速
    utterance.pitch = 1.0;     // 音调
    utterance.volume = 1.0;    // 音量

    // 尝试获取中文语音
    const voices = speechSynthesis.getVoices();
    const chineseVoice = voices.find(voice =>
        voice.lang.includes('zh') || voice.lang.includes('CN')
    );
    if (chineseVoice) {
        utterance.voice = chineseVoice;
    }

    // 播报完成后回调
    utterance.onend = () => {
        console.log('语音播报完成');
    };

    utterance.onerror = (e) => {
        console.error('语音播报失败:', e);
    };

    // 开始播报
    speechSynthesis.speak(utterance);
}