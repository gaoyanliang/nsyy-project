/**
 * 医院急诊一键通知系统 - 前端逻辑
 * Hospital Emergency Notification System - Frontend JavaScript
 */

// 全局变量
let currentUser = { id: 110100, name: 'admin' };
let currentGroup = null;
let departments = [];
let shiftTypes = [];
let shiftTypesLoaded = false;
// 全局存储原始数据
let allDoctors = [];
let allDepartments = [];
const API_BASE = 'http://127.0.0.1:8092/gyl/on_call';

let allDeptOptions = [];   // 存储所有科室 {id, name}
let selectedDepts = [];    // 已选中的科室 {id, name}

// ==================== 初始化 ====================

document.addEventListener('DOMContentLoaded', function() {
    initApp();

    // 在页面初始化或切换到通知页面时调用
    if (document.getElementById('notification-page')) {
        loadDeptCheckboxes();
    }
});

async function initApp() {
    // 加载数据
    await loadTodayDuty();
    await loadGroups();

    loadShiftTypes();

    // 初始化页面
    initNavigation();
    initForms();
    initDutyPage();

    // 设置默认日期
    setDefaultDates();
}

function initNavigation() {
    const navBtns = document.querySelectorAll('.nav-btn');
    navBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const page = this.dataset.page;
            switchPage(page);
        });
    });
}

function switchPage(pageName) {
    // 更新导航按钮状态
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.page === pageName) {
            btn.classList.add('active');
        }
    });

    // 更新页面显示
    document.querySelectorAll('.page').forEach(page => {
        page.classList.remove('active');
    });
    document.getElementById(`${pageName}-page`).classList.add('active');

    // 加载页面数据
    switch (pageName) {
        case 'dashboard':
            loadTodayDuty();
            break;
        case 'duty':
            loadSchedules();
            break;
        case 'notification':
            loadTodayDutyPreview();
            loadNotificationHistory();
            break;
        case 'records':
            loadGroups();
            break;
    }
}

// ==================== 表单初始化 ====================

function initForms() {
    // 急诊通知表单
    document.getElementById('emergency-form').addEventListener('submit', handleEmergencySubmit);
}

function initFilters() {
    // 科室筛选
    loadDepartmentOptions();
}

// ==================== 数据加载函数 ====================
async function loadShiftTypes() {
    try {
        const response = await fetch(`${API_BASE}/shift_types`);
        const data = await response.json();
        shiftTypes = data
        const select = document.getElementById('edit-shift-type');
        if (select) {
            select.innerHTML = shiftTypes.map(type => `<option value="${type}">${type}</option>`).join('');
        }
    } catch(e) {
        console.error('加载班次类型失败', e);
        // 降级使用默认选项
        const defaultTypes = ['主班', '24时班', '白班', '夜班', '正常班', '行政班', '门诊', '休息', '进修', '婚假', '其他'];
        const select = document.getElementById('edit-shift-type');
        select.innerHTML = defaultTypes.map(type => `<option value="${type}">${type}</option>`).join('');
    }
}


async function loadTodayDuty() {
    try {
        const response = await fetch(`${API_BASE}/duty/today`);
        const data = await response.json();

        const container = document.getElementById('today-duty-list');

        // 处理数据结构 - 根据后端返回格式调整
        if (data && Object.keys(data).length > 0) {
            let html = '';
            Object.values(data).forEach(dept => {
                html += `
                    <div class="duty-item">
                        <div class="duty-dept">${dept.dept_name || '未知科室'} (${dept.doctors ? dept.doctors.length : 0}人)</div>
                        <div class="duty-doctors">
                            ${(dept.doctors || []).map(d => `
                                <span class="duty-doctor-tag">
                                    ${d.title || ''} - ${d.doc_name || d.doctor_name || '未知'} (${d.phone || ''}) - ${d.shift_type || d.original_shift || '值班'}
                                </span>
                            `).join('')}
                        </div>
                    </div>
                `;
            });
            container.innerHTML = html || '<p class="empty">今日暂无值班记录</p>';
        } else {
            container.innerHTML = '<p class="empty">今日暂无值班记录</p>';
        }
    } catch (error) {
        console.error('加载今日值班失败:', error);
        document.getElementById('today-duty-list').innerHTML = '<p class="error">加载失败</p>';
    }
}

async function loadTodayDutyPreview() {
    try {
        const response = await fetch(`${API_BASE}/duty/today`);
        const data = await response.json();

        const container = document.getElementById('duty-preview');

        if (data && Object.keys(data).length > 0) {
            let html = '';
            Object.values(data).forEach(dept => {
                (dept.doctors || []).forEach(d => {
                    html += `
                        <div class="duty-preview-item">
                            <span class="duty-preview-name">${d.doc_name || d.doctor_name || '未知'}</span>
                            <span class="duty-preview-dept">${dept.dept_name || '未知科室'}</span>
                        </div>
                    `;
                });
            });
            container.innerHTML = html || '<p class="empty">暂无值班医生</p>';
        } else {
            container.innerHTML = '<p class="empty">今日暂无值班医生</p>';
        }
    } catch (error) {
        console.error('加载值班预览失败:', error);
    }
}

async function loadNotificationHistory() {
    try {
        const response = await fetch(`${API_BASE}/notification/records`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ key: 'all' })
        });
        const data = await response.json();
        const groups = data.data || data || [];

        const container = document.getElementById('notification-history');
        console.log('container', container);
        if (groups.length > 0) {
            let html = '';
            groups.forEach(group => {
                console.log('group', group);
                html += `
                    <div class="history-item" onclick="openGroupDetail(${group.id})">
                        <div class="history-header">
                            <span class="history-patient">${group.patient_name || '未知患者'}</span>
                            <span class="history-time">${formatDateTime(group.created_at)}</span>
                        </div>
                        <div class="history-content">
                            主诉: ${group.patient_info || '暂无'} |
                            参与: ${group.dept_name_list ? group.dept_name_list.split(',').length : 0}个科室
                        </div>
                    </div>
                `;
            });
            container.innerHTML = html;
        } else {
            container.innerHTML = '<p class="empty">暂无通知记录</p>';
        }
    } catch (error) {
        console.error('加载通知历史失败:', error);
    }
}

// ==================== 排班管理 - 网格视图 ====================

let scheduleData = [];
let currentDepartmentFilter = '';
let departmentGrouped = true;

// 初始化排班页面
function initDutyPage() {
    loadDepartmentOptions();
    initMonthSelect();
}

// 初始化月份选择器
function initMonthSelect() {
    const select = document.getElementById('duty-month-select');
    const now = new Date();
    const months = [];

    // 生成最近6个月和未来3个月
    for (let i = -3; i <= 3; i++) {
        const d = new Date(now.getFullYear(), now.getMonth() + i, 1);
        const value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
        const label = `${d.getFullYear()}年${d.getMonth() + 1}月`;
        months.push({ value, label });
    }

    select.innerHTML = months.map(m => `<option value="${m.value}">${m.label}</option>`).join('');

    // 默认选中当前月
    const currentMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
    select.value = currentMonth;
}

// 加载网格视图排班
async function loadScheduleGrid() {
    const monthSelect = document.getElementById('duty-month-select');
    const departmentFilter = document.getElementById('duty-department-filter');
    currentDepartmentFilter = departmentFilter.value;

    const selectedMonth = monthSelect.value;
    if (!selectedMonth) {
        showToast('请选择月份', 'error');
        return;
    }

    const [year, month] = selectedMonth.split('-').map(Number);
    const firstDay = new Date(year, month - 1, 1);
    const lastDay = new Date(year, month, 0);
    const startDate = formatLocalDate(firstDay);
    const endDate = formatLocalDate(lastDay);

    try {
        const response = await fetch(`${API_BASE}/schedules`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                start_date: startDate,
                end_date: endDate,
                dept_id: currentDepartmentFilter
            })
        });

        const result = await response.json();
        scheduleData = result.data || result || [];

        // 生成日期列表
        generateDateHeader(firstDay, lastDay);

        // 生成人员列表
        generatePersonnelList();

        // 生成排班内容
        generateScheduleContent(firstDay, lastDay);

    } catch (error) {
        console.error('加载排班失败:', error);
        showToast('加载排班失败', 'error');
    }
}

// 生成日期头部
function generateDateHeader(firstDay, lastDay) {
    const header = document.getElementById('schedule-date-header');
    const days = [];
    const current = new Date(firstDay);

    while (current <= lastDay) {
        days.push(new Date(current));
        current.setDate(current.getDate() + 1);
    }

    let html = '';
    days.forEach(day => {
        const dayOfWeek = ['日', '一', '二', '三', '四', '五', '六'][day.getDay()];
        const isWeekend = day.getDay() === 0 || day.getDay() === 6;
        const isHoliday = isChineseHoliday(day);
        const weekendClass = (isWeekend || isHoliday) ? ' weekend' : '';

        html += `
            <div class="schedule-cell header-cell date-cell${weekendClass}">
                <div class="date-day">${day.getMonth() + 1}月${day.getDate()}日</div>
                <div class="date-week">${dayOfWeek}</div>
            </div>
        `;
    });

    header.innerHTML = html;
}

// 判断是否为节假日
function isChineseHoliday(date) {
    return false;
}

// 生成人员列表（左侧固定列）
function generatePersonnelList() {
    const personnelList = document.getElementById('schedule-personnel-list');

    if (scheduleData.length === 0) {
        personnelList.innerHTML = '<div class="empty">暂无排班数据</div>';
        return;
    }

    // 按科室分组整理人员
    const groupedData = {};
    scheduleData.forEach(s => {
        const key = s.dept_id || 0;
        if (!groupedData[key]) {
            groupedData[key] = {
                department_name: s.dept_name || '未分组',
                doctors: []
            };
        }

        // 检查是否已添加该医生
        const exists = groupedData[key].doctors.find(d => d.doctor_id === s.doc_id);
        if (!exists) {
            groupedData[key].doctors.push({
                doctor_id: s.doc_id,
                doctor_name: s.doc_name || '未知',
                doctor_title: s.title || '',
                department_name: s.dept_name || ''
            });
        }
    });

    let html = '';

    // 如果启用分组，按科室显示
    if (departmentGrouped) {
        Object.values(groupedData).forEach(group => {
            // 科室标题行
            html += `
                <div class="department-row" onclick="toggleDepartment('${group.department_name}')">
                    <div class="schedule-cell header-cell dept-cell">
                        ${group.department_name}
                        <span class="toggle-icon">▼</span>
                    </div>
                    <div class="schedule-cell header-cell title-cell">-</div>
                    <div class="schedule-cell header-cell name-cell">-</div>
                </div>
            `;

            // 该科室下的医生
            group.doctors.forEach(doc => {
                html += `
                    <div class="personnel-row" data-dept="${group.department_name}">
                        <div class="schedule-cell dept-cell">-</div>
                        <div class="schedule-cell title-cell">${doc.doctor_title || '-'}</div>
                        <div class="schedule-cell name-cell">${doc.doctor_name}</div>
                    </div>
                `;
            });
        });
    } else {
        // 不分组，全部平铺
        let lastDoctorId = null;
        scheduleData.forEach(s => {
            if (s.doc_id !== lastDoctorId) {
                lastDoctorId = s.doc_id;
                html += `
                    <div class="personnel-row">
                        <div class="schedule-cell dept-cell">${s.dept_name || '-'}</div>
                        <div class="schedule-cell title-cell">${s.title || '-'}</div>
                        <div class="schedule-cell name-cell">${s.doc_name || '未知'}</div>
                    </div>
                `;
            }
        });
    }

    personnelList.innerHTML = html;
}

// 生成排班内容（右侧可滚动区域）
function generateScheduleContent(firstDay, lastDay) {
    const content = document.getElementById('schedule-content');
    const days = [];
    const current = new Date(firstDay);

    while (current <= lastDay) {
        days.push(new Date(current));
        current.setDate(current.getDate() + 1);
    }

    // 整理排班数据为二维结构 {doc_id: {date: schedule}}
    const scheduleMap = {};
    scheduleData.forEach(s => {
        if (!scheduleMap[s.doc_id]) {
            scheduleMap[s.doc_id] = {};
        }
        // 处理日期格式
        const dateStr = s.shift_date ? s.shift_date.split('T')[0] : '';
        scheduleMap[s.doc_id][dateStr] = s;
    });

    // 获取人员列表（去重医生）
    const doctors = [];
    const seenDoctors = new Set();
    scheduleData.forEach(s => {
        if (!seenDoctors.has(s.doc_id)) {
            seenDoctors.add(s.doc_id);
            doctors.push({
                doctor_id: s.doc_id,
                doctor_name: s.doc_name || '未知',
                doctor_title: s.title || '',
                department_name: s.dept_name || '',
                department_id: s.dept_id
            });
        }
    });

    let html = '';

    if (departmentGrouped) {
        // 按科室分组显示
        const groupedData = {};
        doctors.forEach(doc => {
            const key = doc.department_id || 0;
            if (!groupedData[key]) {
                groupedData[key] = {
                    department_name: doc.department_name,
                    doctors: []
                };
            }
            groupedData[key].doctors.push(doc);
        });

        Object.values(groupedData).forEach(group => {
            // 科室标题行（空白，为对齐左侧）
            html += '<div class="schedule-row department-row-content">';
            days.forEach(() => {
                html += '<div class="schedule-cell empty-cell"></div>';
            });
            html += '</div>';

            // 医生行
            group.doctors.forEach(doc => {
                html += '<div class="schedule-row">';
                days.forEach(day => {
                    const dateStr = formatLocalDate(day);
                    const schedule = scheduleMap[doc.doctor_id]?.[dateStr];
                    const shiftClass = schedule ? getShiftClass(schedule.shift_type) : '';
                    const cellClass = schedule ? '' : 'empty-cell';
                    const isWeekend = day.getDay() === 0 || day.getDay() === 6;
                    const weekendClass = isWeekend ? ' weekend' : '';

                    if (schedule) {
                        html += `
                            <div class="schedule-cell ${cellClass}${weekendClass} ${shiftClass}"
                                 onclick="openEditModal(${schedule.id}, '${schedule.doc_id}', '${dateStr}', '${schedule.shift_type || ''}', '${schedule.notes || ''}', ${schedule.is_duty || 0}, '${schedule.doc_name}', '${schedule.dept_name}')">
                                ${schedule.shift_type || '-'}
                            </div>
                        `;
                    } else {
                        html += `
                            <div class="schedule-cell ${cellClass}${weekendClass}"
                                 onclick="openNewScheduleModal('${doc.doctor_id}', '${dateStr}', '${doc.doctor_name}', '${doc.department_id}', '${doc.department_name}')">
                                -
                            </div>
                        `;
                    }
                });
                html += '</div>';
            });
        });
    } else {
        // 不分组，全部平铺
        doctors.forEach(doc => {
            html += '<div class="schedule-row">';
            days.forEach(day => {
                const dateStr = formatLocalDate(day);
                const schedule = scheduleMap[doc.doctor_id]?.[dateStr];
                const shiftClass = schedule ? getShiftClass(schedule.shift_type) : '';
                const cellClass = schedule ? '' : 'empty-cell';
                const isWeekend = day.getDay() === 0 || day.getDay() === 6;
                const weekendClass = isWeekend ? ' weekend' : '';

                if (schedule) {
                    html += `
                        <div class="schedule-cell ${cellClass}${weekendClass} ${shiftClass}"
                             onclick="openEditModal(${schedule.id}, '${schedule.doc_id}', '${dateStr}', '${schedule.shift_type || ''}', '${schedule.notes || ''}', ${schedule.is_duty || 0}, '${schedule.doc_name}', '${schedule.dept_name}')">
                            ${schedule.notes || schedule.shift_type || '-'}
                        </div>
                    `;
                } else {
                    html += `
                        <div class="schedule-cell ${cellClass}${weekendClass}"
                             onclick="openNewScheduleModal('${doc.doctor_id}', '${dateStr}', '${doc.doctor_name}', '${doc.department_id}', '${doc.department_name}')">
                            -
                        </div>
                    `;
                }
            });
            html += '</div>';
        });
    }

    content.innerHTML = html;

    // 同步滚动
    setupScrollSync();
}

// 设置左右联动滚动
function setupScrollSync() {
    const left = document.getElementById('schedule-left');
    const right = document.getElementById('schedule-right');
    const dateHeader = document.getElementById('schedule-date-header');

    // 右边滚动时同步左边和日期头部
    right.addEventListener('scroll', function() {
        left.scrollTop = this.scrollTop;
        dateHeader.scrollLeft = this.scrollLeft;
    });

    // 阻止左边滚动影响右边（单向同步：右→左）
    left.addEventListener('scroll', function(e) {
        e.stopPropagation();
    });

    // 阻止日期头部滚动影响右边面板
    dateHeader.addEventListener('scroll', function(e) {
        right.scrollLeft = this.scrollLeft;
        e.stopPropagation();
    });
}

// 切换科室分组视图
function toggleDepartmentView() {
    departmentGrouped = !departmentGrouped;
    loadScheduleGrid();
}

// 打开编辑弹窗（已有排班）
async function openEditModal(id, doctorId, date, shiftType, originalShift, isDuty, doctorName, deptName) {
    await ensureShiftTypesLoaded();
    document.getElementById('edit-schedule-id').value = id;
    document.getElementById('edit-doctor-id').value = doctorId;
    document.getElementById('edit-shift-date').value = date;

    document.getElementById('edit-info-label').innerHTML = `医生：${doctorName} <br><br> 科室：${deptName} <br><br> 日期：${date}`;

    document.getElementById('edit-shift-type').value = shiftType || '正常班';
    document.getElementById('edit-notes').value = originalShift || '';
    document.getElementById('edit-modal-title').textContent = '修改排班';

    document.getElementById('edit-schedule-modal').classList.add('active');
}

// 打开新增弹窗（空白排班）
async function openNewScheduleModal(doctorId, date, doctorName, deptId, deptName) {
    console.log('openNewScheduleModal', doctorId, date, doctorName, deptId, deptName);
    await ensureShiftTypesLoaded();
    document.getElementById('edit-schedule-id').value = '';
    document.getElementById('edit-doctor-id').value = doctorId;
    document.getElementById('edit-shift-date').value = date;
    document.getElementById('edit-info-label').innerHTML = `医生：${doctorName} <br><br> 科室：${deptName} <br><br> 日期：${date}`;
    document.getElementById('edit-shift-type').value = '正常班';
    document.getElementById('edit-notes').value = '';

    document.getElementById('edit-doc-name').value = doctorName;
    document.getElementById('edit-dept-id').value = deptId;
    document.getElementById('edit-dept-name').value = deptName;
    document.getElementById('edit-modal-title').textContent = '新增排班';

    document.getElementById('edit-schedule-modal').classList.add('active');
}

// 关闭编辑弹窗
function closeEditModal() {
    document.getElementById('edit-schedule-modal').classList.remove('active');
}

// 保存排班
async function saveScheduleFromModal() {
    const id = document.getElementById('edit-schedule-id').value;
    const doctorId = document.getElementById('edit-doctor-id').value;
    let doctorName = document.getElementById('edit-doc-name').value;
    const date = document.getElementById('edit-shift-date').value;
    const shiftType = document.getElementById('edit-shift-type').value;
    const originalShift = document.getElementById('edit-notes').value;

    const payload = {
        doc_id: doctorId,
        doc_name: doctorName,
        shift_date: date,
        shift_type: shiftType,
        notes: originalShift
    };

    try {
        let response;
        if (id) {
            // 更新
            payload.id = id;
            response = await fetch(`${API_BASE}/update_schedules`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        } else {
            // 新增
            let deptId = document.getElementById('edit-dept-id').value;
            let deptName = document.getElementById('edit-dept-name').value;
            if (!doctorName || !deptId || !deptName) {
                showToast('缺少医生或科室信息', 'error');
                return;
            }

            payload.dept_id = deptId;
            payload.dept_name = deptName;
            response = await fetch(`${API_BASE}/new_schedules`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        }

        const result = await response.json();
        if (result.success !== false) {
            showToast('保存成功', 'success');
            closeEditModal();
            loadScheduleGrid();
        } else {
            showToast(result.error || '保存失败', 'error');
        }
    } catch (error) {
        console.error('保存排班失败:', error);
        showToast('保存失败', 'error');
    }
}

// 删除排班
async function deleteScheduleFromModal() {
    const id = document.getElementById('edit-schedule-id').value;
    if (!id) {
        showToast('无排班记录可删除', 'error');
        return;
    }

    if (!confirm('确定要删除这条排班记录吗？')) return;

    try {
        const response = await fetch(`${API_BASE}/schedules/`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ id: id })
        });
        const result = await response.json();

        if (result.success !== false) {
            showToast('删除成功', 'success');
            closeEditModal();
            loadScheduleGrid();
        } else {
            showToast(result.error || '删除失败', 'error');
        }
    } catch (error) {
        console.error('删除排班失败:', error);
        showToast('删除失败', 'error');
    }
}

// 保留原有的loadSchedules函数以兼容其他功能
async function loadSchedules() {
    loadScheduleGrid();
}

function getShiftClass(shiftType) {
    switch (shiftType) {
        case '主班': return 'shift-main';
        case '夜班': return 'shift-night';
        case '副班': return 'shift-main';
        case '正常班': return 'shift-normal';
        case '休息': return 'shift-off';
        default: return 'shift-normal';
    }
}

// ==================== 一键通知 ====================

async function loadDeptCheckboxes() {
    try {
        await fetchDepartments();
        const deptMap = new Map();
        allDepartments.forEach(s => {
            if (s.his_dept_id && s.dept_name) {
                deptMap.set(s.his_dept_id, s.dept_name);
            }
        });
        allDepartments.forEach(s => {
            if (s.his_dept_id && s.dept_name && !deptMap.has(s.his_dept_id)) {
                deptMap.set(s.his_dept_id, s.dept_name);
            }
        });
        allDeptOptions = Array.from(deptMap.entries()).map(([id, name]) => ({ id, name }));
        // 清空已选
        selectedDepts = [];
        renderSelectedTags();
        renderDeptDropdown('');

        // 确保下拉框初始隐藏
        const dropdown = document.getElementById('dept-dropdown');
        if (dropdown) dropdown.style.display = 'none';

        // 重新绑定搜索输入事件（确保不重复绑定）
        const searchInput = document.getElementById('dept-search-input');
        if (searchInput) {
            searchInput.oninput = (e) => filterDeptOptions(e.target.value);
        }
    } catch(e) {
        console.error('加载科室列表失败', e);
        const container = document.getElementById('dept-options-list');
        if (container) container.innerHTML = '<div class="option">加载失败，请刷新重试</div>';

    }
}

function renderDeptDropdown(filterText = '') {
    const container = document.getElementById('dept-options-list');
    if (!container) return;
    const filtered = allDeptOptions.filter(d => d.name.includes(filterText));
    if (filtered.length === 0) {
        container.innerHTML = '<div class="option">无匹配科室</div>';
    } else {
        container.innerHTML = filtered.map(d => `
            <div class="option ${selectedDepts.some(s => s.id == d.id) ? 'selected' : ''}"
                 data-id="${d.id}" data-name="${d.name.replace(/"/g, '&quot;')}"
                 onclick="toggleDeptSelection(this)">
                ${d.name}
            </div>
        `).join('');
    }
}

function toggleDeptSelection(element) {
    const id = element.getAttribute('data-id');
    const name = element.getAttribute('data-name');
    const index = selectedDepts.findIndex(d => d.id == id);
    if (index === -1) {
        selectedDepts.push({ id, name });
    } else {
        selectedDepts.splice(index, 1);
    }
    renderSelectedTags();
    // 刷新下拉选项的高亮状态
    renderDeptDropdown(document.getElementById('dept-search-input').value);
    updateDutyPreview();  // 更新值班预览
}

function renderSelectedTags() {
    const container = document.getElementById('selected-dept-tags');
    if (!container) return;
    container.innerHTML = selectedDepts.map(d => `
        <span class="tag">
            ${d.name}
            <span class="tag-remove" onclick="event.stopPropagation(); removeDeptTag('${d.id}')">×</span>
        </span>
    `).join('');
}

function removeDeptTag(id) {
    selectedDepts = selectedDepts.filter(d => d.id != id);
    renderSelectedTags();
    renderDeptDropdown(document.getElementById('dept-search-input').value);
    updateDutyPreview();
}

function toggleDeptDropdown() {
    const dropdown = document.getElementById('dept-dropdown');
    if (!dropdown) return;
    if (dropdown.style.display === 'none') {
        dropdown.style.display = 'block';
        // 重新渲染下拉选项（确保最新）
        renderDeptDropdown(document.getElementById('dept-search-input').value);
    } else {
        dropdown.style.display = 'none';
    }
}

function filterDeptOptions(value) {
    renderDeptDropdown(value);
}

// 点击其他地方关闭下拉框
document.addEventListener('click', function(e) {
    const container = document.getElementById('multi-select-dept');
    const dropdown = document.getElementById('dept-dropdown');
    if (container && !container.contains(e.target) && dropdown) {
        dropdown.style.display = 'none';
    }
});

async function updateDutyPreview() {
    if (selectedDepts.length === 0) {
        document.getElementById('duty-preview').innerHTML = '<p class="empty">请选择科室查看值班医生</p>';
        return;
    }
    try {
        const response = await fetch(`${API_BASE}/duty/today`);
        const dutyData = await response.json();
        console.log('值班数据:', dutyData);

        let html = '';
        for (let dept of selectedDepts) {
            const deptId = dept.id;
            const deptName = dept.name;
            const deptInfo = dutyData[deptId];
            if (deptInfo && deptInfo.doctors && deptInfo.doctors.length) {
                deptInfo.doctors.forEach(doc => {
                    html += `<div class="duty-preview-item">
                                <span class="duty-preview-name">${doc.doc_name}</span>
                                <span class="duty-preview-dept">${deptInfo.dept_name} (${doc.shift_type || '值班'})</span>
                            </div>`;
                });
            } else {
                html += `<div class="duty-preview-item">科室 ${deptName} 今日无值班医生</div>`;
            }
        }
        document.getElementById('duty-preview').innerHTML = html || '<p class="empty">所选科室今日无值班医生</p>';
    } catch(e) {
        console.error('加载值班预览失败', e);
        document.getElementById('duty-preview').innerHTML = '<p class="error">加载失败</p>';
    }
}

async function handleEmergencySubmit(e) {
    e.preventDefault();

    const patientName = document.getElementById('patient-name').value.trim();
    const patientGender = document.getElementById('patient-gender').value;
    const patientAge = document.getElementById('patient-age').value;
    const patientCondition = document.getElementById('patient-condition').value.trim();

    if (!patientName || !patientCondition) {
        showToast('请填写患者姓名和患者情况', 'error');
        return;
    }

    if (selectedDepts.length === 0) {
        showToast('请至少选择一个会诊科室', 'error');
        return;
    }

    // 构建患者情况字符串（包含年龄、性别、主诉等）
    let patientInfo = `年龄：${patientAge || '未知'}，性别：${patientGender}，情况：${patientCondition}`;

    const data = {
        patient_name: patientName,
        patient_info: patientInfo,
        dept_list: selectedDepts,
        sender_id: currentUser.id,
        sender_name: currentUser.name
    };

    try {
        const response = await fetch(`${API_BASE}/notification/emergency`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (result.success !== false) {
            showToast('会诊通知已发送', 'success');
            // 清空表单
            document.getElementById('emergency-form').reset();
            // 刷新数据
            loadNotificationHistory();
            selectedDepts = [];
        } else {
            showToast(result.error || '通知失败', 'error');
        }
    } catch (error) {
        console.error('发送通知失败:', error);
        showToast('发送通知失败', 'error');
    }
    selectedDepts = [];
}

// ==================== 会诊记录 ====================

async function loadGroups() {
    const status = document.getElementById('group-status-filter').value;
    try {
        const response = await fetch(`${API_BASE}/notification/records`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ key: 'all' })
        });
        const result = await response.json();
        const groups = result.data || result || [];

        const container = document.getElementById('groups-list');
        if (groups.length > 0) {
            let html = '';
            groups.forEach(group => {
                const isActive = group.status === 1 || group.status === '进行中';
                const statusClass = isActive ? 'status-active' : 'status-closed';
                const statusText = isActive ? '进行中' : '进行中';

                html += `
                    <div class="group-item" onclick="openGroupDetail(${group.id})">
                        <div class="group-header">
                            <span class="group-patient">${group.patient_name || '未知患者'}</span>
                            <span class="group-status ${statusClass}">${statusText}</span>
                        </div>
                        <div class="group-info">
                            <span>主诉: ${group.patient_info ? group.patient_info.split('\n')[0] : '暂无'}</span>
                            <span>科室: ${group.dept_name_list ? group.dept_name_list.split(',').length : 0}个</span>
                        </div>
                        <div class="group-time">${formatDateTime(group.created_at)}</div>
                    </div>
                `;
            });
            container.innerHTML = html;
        } else {
            container.innerHTML = '<p class="empty">暂无会诊记录</p>';
        }
    } catch (error) {
        console.error('加载会诊记录失败:', error);
        document.getElementById('groups-list').innerHTML = '<p class="error">加载失败</p>';
    }
}

async function openGroupDetail(recordId) {
    console.log('打开会诊详情', recordId);
    try {
        const response = await fetch(`${API_BASE}/notification/record/detail`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                record_id: recordId
            })
        });
        const result = await response.json();
        const group = result.data || result || [];

        currentGroup = { id: recordId };

        console.log('会诊详情', group);

        // 更新模态框内容
        document.getElementById('modal-group-title').textContent = `会诊 - ${group.patient_name || '未知患者'}`;
        document.getElementById('modal-patient-name').textContent = group.patient_name || '未知';
        document.getElementById('modal-chief-complaint').textContent = group.patient_info || '暂无';
        document.getElementById('modal-member-dept').textContent = group.dept_name_list || '';
        document.getElementById('modal-member-count').textContent = group.doctors ? group.doctors.length : 0;

        // 渲染成员（科室）
        const membersContainer = document.getElementById('modal-members');
        if (group.dept_name_list) {
            const depts = group.doctors;
            membersContainer.innerHTML = depts.map(dept => `
                <div class="member-card">
                    <div class="member-name">${dept.doc_name}</div>
                    <div class="member-dept">${dept.dept_name}</div>
                </div>
            `).join('');
        } else {
            membersContainer.innerHTML = '<p class="empty">暂无科室</p>';
        }

        console.log('会诊详情渲染成功');

        // 渲染消息 - 需要单独获取
        loadMessages(recordId);

        console.log('会诊详情消息渲染成功');

        // 显示模态框
        document.getElementById('group-detail-modal').classList.add('active');

        console.log('会诊渲染成功');

    } catch (error) {
        console.error('加载会诊详情失败:', error);
        showToast('加载会诊详情失败', 'error');
    }
}

async function loadMessages(recordId) {
    const messagesContainer = document.getElementById('modal-messages');
    if (!messagesContainer) return;

    try {

        const response = await fetch(`${API_BASE}/record/message`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ record_id: recordId })
        });
        const result = await response.json();
        // 处理后端返回格式（可能是 {code:20000, data: [...]} 或直接数组）
        let messages = [];
        if (result.code === 20000) {
            messages = result.data || [];
        } else if (Array.isArray(result)) {
            messages = result;
        } else {
            messages = result.data || result || [];
        }

        if (messages.length === 0) {
            messagesContainer.innerHTML = '<p class="empty">暂无消息记录</p>';
            return;
        }

        // 按时间升序排列（确保旧消息在上，新消息在下）
        messages.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));

        const html = messages.map(msg => {
            // 根据消息类型添加样式类
            let msgClass = 'message-normal';
            if (msg.content && msg.content.includes('【急诊会诊通知】')) {
                msgClass = 'message-notification';
            } else if (msg.content && (msg.content.includes('已通知医生') || msg.content.includes('会诊'))) {
                msgClass = 'message-system';
            }
            return `
                <div class="message-item ${msgClass}">
                    <div class="message-sender">${escapeHtml(msg.sender_name || '系统')}</div>
                    <div class="message-content">${escapeHtml(msg.content || '')}</div>
                    <div class="message-time">${formatDateTime(msg.created_at)}</div>
                </div>
            `;
        }).join('');

        messagesContainer.innerHTML = html;
        // 滚动到底部显示最新消息
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    } catch (error) {
        console.error('加载消息记录失败:', error);
        messagesContainer.innerHTML = '<p class="error">加载消息失败</p>';
    }
}

// 辅助函数：防止XSS
function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>]/g, function(m) {
        if (m === '&') return '&amp;';
        if (m === '<') return '&lt;';
        if (m === '>') return '&gt;';
        return m;
    }).replace(/[\uD800-\uDBFF][\uDC00-\uDFFF]/g, function(c) {
        return c;
    });
}

function closeGroupModal() {
    document.getElementById('group-detail-modal').classList.remove('active');
    currentGroup = null;
}

async function sendMessage() {
    const input = document.getElementById('message-input');
    const content = input.value.trim();

    if (!content || !currentGroup) {
        return;
    }

    try {
        await fetch(`${API_BASE}/notification/record/message`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                record_id: currentGroup.id,
                sender_id: currentUser.id,
                sender_name: currentUser.name,
                message: content
            })
        });

        input.value = '';
        showToast('消息已发送', 'success');
        loadMessages(currentGroup.id);
    } catch (error) {
        console.error('发送消息失败:', error);
        showToast('发送消息失败', 'error');
    }
}


async function closeConsultation() {
    if (!currentGroup) return;
    showToast('会诊已关闭', 'success');
    closeGroupModal();
    loadGroups();
}

// ==================== 复制排班 ====================

function showCopyScheduleModal() {
    const today = new Date();
    const lastWeekStart = new Date(today);
    lastWeekStart.setDate(today.getDate() - 7);
    const lastWeekEnd = new Date(today);
    lastWeekEnd.setDate(today.getDate() - 1);

    const nextWeekStart = new Date(today);
    nextWeekStart.setDate(today.getDate() + 1);
    const nextWeekEnd = new Date(today);
    nextWeekEnd.setDate(today.getDate() + 7);

    const formatDate = (date) => formatLocalDate(date);

    document.getElementById('source-start').value = formatDate(lastWeekStart);
    document.getElementById('source-end').value = formatDate(lastWeekEnd);
    document.getElementById('target-start').value = formatDate(nextWeekStart);
    document.getElementById('target-end').value = formatDate(nextWeekEnd);

    document.getElementById('copy-schedule-modal').classList.add('active');
}

function closeCopyModal() {
    document.getElementById('copy-schedule-modal').classList.remove('active');
}

function quickCopy(type) {
    const today = new Date();

    if (type === 'week') {
        const lastWeekStart = new Date(today);
        lastWeekStart.setDate(today.getDate() - 7);
        const lastWeekEnd = new Date(today);
        lastWeekEnd.setDate(today.getDate() - 1);

        const nextWeekStart = new Date(today);
        nextWeekStart.setDate(today.getDate() + 1);
        const nextWeekEnd = new Date(today);
        nextWeekEnd.setDate(today.getDate() + 7);

        const formatDate = (date) => formatLocalDate(date);

        document.getElementById('source-start').value = formatDate(lastWeekStart);
        document.getElementById('source-end').value = formatDate(lastWeekEnd);
        document.getElementById('target-start').value = formatDate(nextWeekStart);
        document.getElementById('target-end').value = formatDate(nextWeekEnd);
    } else if (type === 'month') {
        const lastMonthStart = new Date(today.getFullYear(), today.getMonth() - 1, 1);
        const lastMonthEnd = new Date(today.getFullYear(), today.getMonth(), 0);

        const nextMonthStart = new Date(today.getFullYear(), today.getMonth(), 1);
        const nextMonthEnd = new Date(today.getFullYear(), today.getMonth() + 1, 0);

        const formatDate = (date) => formatLocalDate(date);

        document.getElementById('source-start').value = formatDate(lastMonthStart);
        document.getElementById('source-end').value = formatDate(lastMonthEnd);
        document.getElementById('target-start').value = formatDate(nextMonthStart);
        document.getElementById('target-end').value = formatDate(nextMonthEnd);
    }
}

async function copySchedule() {
    const sourceStart = document.getElementById('source-start').value;
    const sourceEnd = document.getElementById('source-end').value;
    const targetStart = document.getElementById('target-start').value;
    const targetEnd = document.getElementById('target-end').value;

    if (!sourceStart || !sourceEnd || !targetStart || !targetEnd) {
        showToast('请填写完整的时间段', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/schedules/copy`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                source_start: sourceStart,
                source_end: sourceEnd,
                target_start: targetStart,
                target_end: targetEnd
            })
        });

        const result = await response.json();

        if (result.success !== false) {
            showToast('复制成功', 'success');
            closeCopyModal();
            loadScheduleGrid();
        } else {
            showToast(result.error || '复制失败', 'error');
        }
    } catch (error) {
        console.error('复制排班失败:', error);
        showToast('复制排班失败', 'error');
    }
}

// ==================== 导入导出 ====================

function showImportModal() {
    document.getElementById('import-file').value = '';
    document.getElementById('import-modal').classList.add('active');
}

function closeImportModal() {
    document.getElementById('import-modal').classList.remove('active');
}

async function importSchedules() {
    showToast('导入功能开发中', 'info');
    closeImportModal();
}

async function exportSchedules() {
    if (!scheduleData || scheduleData.length === 0) {
        showToast('暂无排班数据可导出', 'error');
        return;
    }

    // 定义CSV列头
    const headers = ['医生ID', '医生姓名', '科室ID', '科室名称', '值班日期', '班次类型', '说明'];
    const rows = scheduleData.map(s => [
        s.doc_id,
        s.doc_name,
        s.dept_id,
        s.dept_name,
        s.shift_date,
        s.shift_type,
        s.notes || ''
    ]);

    const csvContent = [headers, ...rows].map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(',')).join('\n');
    const blob = new Blob(["\uFEFF" + csvContent], { type: 'text/csv;charset=utf-8;' }); // 添加BOM解决中文乱码
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    link.href = url;
    link.setAttribute('download', `排班表_${formatLocalDate(new Date())}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    showToast('导出成功');
}


// 初始化可搜索下拉框
function initSearchableSelect(inputId, optionsContainerId, dataArray, displayKey, valueKey, hiddenInputId, onSelectCallback) {
    const input = document.getElementById(inputId);
    const container = document.getElementById(optionsContainerId);
    if (!input || !container) return;

    // 显示选项
    function renderOptions(filterText = '') {
        const filtered = dataArray.filter(item => {
            let display = '';
            if (typeof displayKey === 'function') {
                display = displayKey(item).toLowerCase();
            } else {
                display = (item[displayKey] || '').toLowerCase();
            }
            return display.includes(filterText.toLowerCase());
        });
        container.innerHTML = '';
        if (filtered.length === 0) {
            const emptyDiv = document.createElement('div');
            emptyDiv.className = 'option-item';
            emptyDiv.textContent = '无匹配项';
            container.appendChild(emptyDiv);
        } else {
            filtered.forEach(item => {
                const div = document.createElement('div');
                div.className = 'option-item';
                const displayText = typeof displayKey === 'function' ? displayKey(item) : item[displayKey];
                div.textContent = displayText;
                div.dataset.value = item[valueKey];
                div.dataset.data = JSON.stringify(item);
                div.onclick = () => {
                    input.value = displayText;
                    const hidden = document.getElementById(hiddenInputId);
                    if (hidden) hidden.value = item[valueKey];
                    if (onSelectCallback) onSelectCallback(item);
                    container.style.display = 'none';
                };
                container.appendChild(div);
            });
        }
        container.style.display = 'block';
    }

    input.addEventListener('input', () => renderOptions(input.value));
    input.addEventListener('focus', () => renderOptions(input.value));
    document.addEventListener('click', function(e) {
        if (!input.contains(e.target) && !container.contains(e.target)) {
            container.style.display = 'none';
        }
    });
}

// 显示新增排班模态框
async function showAddScheduleModal() {
    await ensureShiftTypesLoaded();
    await fetchDoctors();
    await fetchDepartments();

    // 初始化医生选择器
    initSearchableSelect('doctor-search', 'doctor-options', allDoctors,
        'doc_name',
        'doc_id',
        'selected-doctor-id',
    );

    // 初始化科室选择器
    initSearchableSelect('dept-search', 'dept-options', allDepartments,
        'dept_name',
        'his_dept_id',
        'selected-dept-id',
    );

    // 填充班次类型
    const shiftSelect = document.getElementById('add-shift-type');
    shiftSelect.innerHTML = shiftTypes.map(t => `<option value="${t}">${t}</option>`).join('');

    // 设置默认日期
    document.getElementById('add-shift-date').value = formatLocalDate(new Date());
    document.getElementById('add-notes').value = '';

    // 清空输入框
    document.getElementById('doctor-search').value = '';
    document.getElementById('dept-search').value = '';
    document.getElementById('selected-doctor-id').value = '';
    document.getElementById('selected-dept-id').value = '';

    // 显示模态框
    document.getElementById('add-schedule-modal').classList.add('active');
}

function closeAddScheduleModal() {
    document.getElementById('add-schedule-modal').classList.remove('active');
}

async function submitAddSchedule() {
    const docId = document.getElementById('selected-doctor-id').value;
    const deptId = document.getElementById('selected-dept-id').value;
    const shiftDate = document.getElementById('add-shift-date').value;
    const shiftType = document.getElementById('add-shift-type').value;
    const notes = document.getElementById('add-notes').value;

    if (!docId || !deptId || !shiftDate || !shiftType) {
        showToast('请完整填写信息', 'error');
        return;
    }

    // 从原始数据中获取医生和科室详细信息
    const doctor = allDoctors.find(d => d.doc_id == docId);
    const dept = allDepartments.find(d => d.his_dept_id == deptId);
    if (!doctor || !dept) {
        showToast('人员或科室信息无效', 'error');
        return;
    }

    const body = {
        doc_id: docId,
        doc_name: doctor.doc_name,
        dept_id: deptId,
        dept_name: dept.dept_name,
        shift_date: shiftDate,
        shift_type: shiftType,
        notes: notes
    };

    try {
        response = await fetch(`${API_BASE}/new_schedules`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        const result = await response.json();

        if (result.code == 20000) {
            showToast('新增成功', 'success');
            closeAddScheduleModal();
            loadScheduleGrid();
        } else {
            showToast(result.error || '复制失败', 'error');
        }
    } catch(e) {
        console.log('新增失败', e);
        showToast('新增失败', 'error', );
    }
}

function closeAddScheduleModal() {
    const modal = document.getElementById('add-schedule-modal');
    if (modal) modal.classList.remove('active');

    // 清空医生搜索框及选项
    const doctorSearch = document.getElementById('doctor-search');
    if (doctorSearch) doctorSearch.value = '';
    const doctorOptions = document.getElementById('doctor-options');
    if (doctorOptions) doctorOptions.style.display = 'none';

    // 清空科室搜索框及选项
    const deptSearch = document.getElementById('dept-search');
    if (deptSearch) deptSearch.value = '';
    const deptOptions = document.getElementById('dept-options');
    if (deptOptions) deptOptions.style.display = 'none';

    // 清空隐藏域
    const selectedDoctor = document.getElementById('selected-doctor-id');
    if (selectedDoctor) selectedDoctor.value = '';
    const selectedDept = document.getElementById('selected-dept-id');
    if (selectedDept) selectedDept.value = '';
}

// 获取医生列表
async function fetchDoctors() {
    try {
        const response = await fetch(`${API_BASE}/doctors`, {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' }
        });

        const result = await response.json();

        if (result.code == 20000) {
            allDoctors = result.data;
            return result.data;
        } else {
            return  [];
        }
    } catch(e) {
        console.error('获取医生列表失败', e);
        return [];
    }
}

// 获取科室列表
async function fetchDepartments() {
    try {
        const response = await fetch(`${API_BASE}/depts`, {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' }
        });

        const result = await response.json();

        if (result.code == 20000) {
            allDepartments = result.data;
            return result.data;
        } else {
            return  [];
        }
    } catch(e) {
        console.error('获取科室列表失败', e);
        return [];
    }
}


// ==================== 科室选项 ====================

async function loadDepartmentOptions() {
    // 由于后端没有单独提供科室列表接口，暂时使用空实现
    // 后续可以扩展
    const select = document.getElementById('duty-department-filter');
    select.innerHTML = '<option value="">全部科室</option>';
}

// ==================== 工具函数 ====================

async function ensureShiftTypesLoaded() {
    if (!shiftTypesLoaded && shiftTypes.length === 0) {
        await loadShiftTypes();
        shiftTypesLoaded = true;
    }
}

function formatLocalDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}


function formatDateTime(createdAt) {
    if (!createdAt) return '';

    // "Tue, 19 May 2026 18:29:57 GMT"
    const date = new Date(createdAt);

    const Y = date.getUTCFullYear();
    const M = String(date.getUTCMonth() + 1).padStart(2, '0');
    const D = String(date.getUTCDate()).padStart(2, '0');
    const h = String(date.getUTCHours()).padStart(2, '0');
    const m = String(date.getUTCMinutes()).padStart(2, '0');
    const s = String(date.getUTCSeconds()).padStart(2, '0');

    return `${Y}-${M}-${D} ${h}:${m}:${s}`;
}

function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type} active`;

    setTimeout(() => {
        toast.classList.remove('active');
    }, 3000);
}

// 绑定回车发送消息
document.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && document.getElementById('message-input') && document.activeElement.id === 'message-input') {
        sendMessage();
    }
});

function setDefaultDates() {
    // 设置复制排班模态框的默认日期
}