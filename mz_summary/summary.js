// ======================== 智慧候诊排队系统 - JavaScript逻辑 ========================

// ======================== 全局变量配置 ========================

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


let ws = null;
let businessTypes = {};
let skippedPatients = [];
let currentPageIndex = 0;
let totalPages = 0;
let carouselInterval = null;
const CAROUSEL_INTERVAL_MS = 5000;

// 存储每个业务队列轮播实例
const boardCarousels = new Map();

// 当前叫号轮播变量
let currentCallsData = [];
let callsPagesArray = [];
let callsCurrentPage = 0;
let callsAutoInterval = null;
const CALLS_PAGE_SIZE = 5;
const CALLS_AUTO_INTERVAL = 5000;

// ======================== 辅助函数 ========================

/**
 * HTML转义，防止XSS攻击
 * @param {string} str - 需要转义的字符串
 * @returns {string} 转义后的字符串
 */
function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>]/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[m]));
}

/**
 * 格式化时间显示
 * @param {string} timeStr - ISO格式时间字符串
 * @returns {string} 格式化后的时间文本
 */
function formatTime(timeStr) {
    if (!timeStr) return '';
    const date = new Date(timeStr);
    const now = new Date();
    const diff = Math.floor((now - date) / 60000);
    if (diff < 1) return '刚刚';
    if (diff < 60) return `${diff}分钟前`;
    return `${Math.floor(diff / 60)}小时前`;
}

/**
 * 深色化颜色值
 * @param {string} color - 原始颜色值
 * @returns {string} 深色化后的颜色值
 */
function darkenColor(color) {
    const map = {
        '#3B82F6': '#2563EB',
        '#8B5CF6': '#7C3AED',
        '#10B981': '#059669',
        '#F59E0B': '#D97706'
    };
    return map[color] || color;
}

// ======================== 当前叫号轮播功能 ========================

/**
 * 构建叫号页面数据
 * @param {Array} calls - 叫号数据数组
 * @returns {Array} 分页后的页面数组
 */
function buildCallsPages(calls) {
    const pages = [];
    if (!calls || calls.length === 0) return [];
    for (let i = 0; i < calls.length; i += CALLS_PAGE_SIZE) {
        pages.push(calls.slice(i, i + CALLS_PAGE_SIZE));
    }
    return pages;
}

/**
 * 创建叫号卡片元素
 * @param {Object} call - 叫号数据对象
 * @returns {HTMLElement} 卡片DOM元素
 */
function createCallCard(call) {
    const cardDiv = document.createElement('div');
    cardDiv.className = 'call-card';
    cardDiv.innerHTML = `
        <div class="call-window">${escapeHtml(call.window_name || '窗口')}</div>
        <div class="call-number">${escapeHtml(call.queue_number)}</div>
        <div class="call-footer">
            <span class="call-patient">${escapeHtml(call.patient_name || '患者')}</span>
            <div class="call-business">
                <svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2">
                    <circle cx="12" cy="12" r="10"/>
                </svg>
                ${escapeHtml(call.business_name || '')}
            </div>
        </div>
    `;
    return cardDiv;
}

/**
 * 渲染叫号轮播
 */
function renderCallsCarousel() {
    const track = document.getElementById('callsTrack');
    if (!track) return;

    callsPagesArray = buildCallsPages(currentCallsData);
    track.innerHTML = '';

    if (callsPagesArray.length === 0) {
        const emptyPage = document.createElement('div');
        emptyPage.className = 'calls-page';
        emptyPage.innerHTML = `<div class="empty-calls" style="grid-column:1/-1;">暂无正在呼叫的号码</div>`;
        track.appendChild(emptyPage);
        callsCurrentPage = 0;
        updateCallsDots();
        updateCallsArrowState();
        stopCallsAutoScroll();
        return;
    }

    for (let pageData of callsPagesArray) {
        const pageDiv = document.createElement('div');
        pageDiv.className = 'calls-page';
        for (let i = 0; i < CALLS_PAGE_SIZE; i++) {
            if (i < pageData.length) {
                pageDiv.appendChild(createCallCard(pageData[i]));
            } else {
                const ph = document.createElement('div');
                ph.style.visibility = 'hidden';
                ph.style.height = '90px';
                pageDiv.appendChild(ph);
            }
        }
        track.appendChild(pageDiv);
    }

    if (callsCurrentPage >= callsPagesArray.length) callsCurrentPage = 0;
    updateCallsTrackTransform();
    updateCallsDots();
    updateCallsArrowState();
    startCallsAutoScroll();
}

/**
 * 更新叫号轨道位置
 */
function updateCallsTrackTransform() {
    const track = document.getElementById('callsTrack');
    if (track && callsPagesArray.length > 0) {
        track.style.transform = `translateX(-${callsCurrentPage * 100}%)`;
    }
}

/**
 * 更新叫号指示点
 */
function updateCallsDots() {
    const dotsContainer = document.getElementById('callsDots');
    if (!dotsContainer) return;

    dotsContainer.innerHTML = '';

    if (callsPagesArray.length <= 1) {
        dotsContainer.style.display = 'none';
        return;
    }

    dotsContainer.style.display = 'flex';
    for (let i = 0; i < callsPagesArray.length; i++) {
        const dot = document.createElement('div');
        dot.className = `calls-dot ${i === callsCurrentPage ? 'active' : ''}`;
        dot.addEventListener('click', () => {
            stopCallsAutoScroll();
            callsCurrentPage = i;
            updateCallsTrackTransform();
            updateCallsDots();
            startCallsAutoScroll();
        });
        dotsContainer.appendChild(dot);
    }
}

/**
 * 更新叫号箭头状态
 */
function updateCallsArrowState() {
    const prev = document.getElementById('callsPrevBtn');
    const next = document.getElementById('callsNextBtn');
    const show = callsPagesArray.length > 1;
    if (prev) prev.style.visibility = show ? 'visible' : 'hidden';
    if (next) next.style.visibility = show ? 'visible' : 'hidden';
}

/**
 * 下一页
 */
function nextCallsPage() {
    if (callsPagesArray.length) {
        callsCurrentPage = (callsCurrentPage + 1) % callsPagesArray.length;
        updateCallsTrackTransform();
        updateCallsDots();
    }
}

/**
 * 上一页
 */
function prevCallsPage() {
    if (callsPagesArray.length) {
        callsCurrentPage = (callsCurrentPage - 1 + callsPagesArray.length) % callsPagesArray.length;
        updateCallsTrackTransform();
        updateCallsDots();
    }
}

/**
 * 开始叫号自动轮播
 */
function startCallsAutoScroll() {
    stopCallsAutoScroll();
    if (callsPagesArray.length > 1) {
        callsAutoInterval = setInterval(nextCallsPage, CALLS_AUTO_INTERVAL);
    }
}

/**
 * 停止叫号自动轮播
 */
function stopCallsAutoScroll() {
    if (callsAutoInterval) {
        clearInterval(callsAutoInterval);
        callsAutoInterval = null;
    }
}

/**
 * 绑定叫号轮播悬停事件
 */
function bindCallsCarouselHover() {
    const container = document.getElementById('callsCarouselContainer');
    if (container) {
        container.addEventListener('mouseenter', stopCallsAutoScroll);
        container.addEventListener('mouseleave', startCallsAutoScroll);
    }
}

// ======================== 等候队列独立轮播组件 ========================

/**
 * 队列独立轮播类 - 每个业务窗口独立轮播
 */
class QueueBoardCarousel {
    /**
     * 构造函数
     * @param {HTMLElement} containerElement - 轮播容器元素
     * @param {string} businessId - 业务ID
     * @param {number} pageSize - 每页显示数量
     * @param {number} autoInterval - 自动轮播间隔
     */
    constructor(containerElement, businessId, pageSize = 5, autoInterval = 5000) {
        this.container = containerElement;
        this.businessId = businessId;
        this.pageSize = pageSize;
        this.autoIntervalMs = autoInterval;
        this.items = [];
        this.pages = [];
        this.currentPage = 0;
        this.timer = null;
        this.isHovering = false;
        this.initDom();
        this.bindEvents();
    }

    /**
     * 初始化DOM结构
     */
    initDom() {
        if (!this.container.querySelector('.queue-carousel-inner')) {
            this.container.innerHTML = `
                <div class="queue-carousel-inner">
                    <div class="queue-carousel-wrapper">
                        <button class="queue-carousel-btn prev-queue-btn" data-id="${this.businessId}">‹</button>
                        <div class="queue-viewport">
                            <div class="queue-track"></div>
                        </div>
                        <button class="queue-carousel-btn next-queue-btn" data-id="${this.businessId}">›</button>
                    </div>
                    <div class="queue-carousel-dots" data-id="${this.businessId}"></div>
                </div>
            `;
        }
        this.track = this.container.querySelector('.queue-track');
        this.dotsContainer = this.container.querySelector('.queue-carousel-dots');
        this.prevBtn = this.container.querySelector('.prev-queue-btn');
        this.nextBtn = this.container.querySelector('.next-queue-btn');
    }

    /**
     * 绑定事件
     */
    bindEvents() {
        if (this.prevBtn) {
            this.prevBtn.addEventListener('click', () => {
                this.stopAuto();
                this.prevPage();
                this.startAuto();
            });
        }
        if (this.nextBtn) {
            this.nextBtn.addEventListener('click', () => {
                this.stopAuto();
                this.nextPage();
                this.startAuto();
            });
        }
        const wrapper = this.container.querySelector('.queue-carousel-wrapper');
        if (wrapper) {
            wrapper.addEventListener('mouseenter', () => this.stopAuto());
            wrapper.addEventListener('mouseleave', () => this.startAuto());
        }
    }

    /**
     * 设置数据并开始轮播
     * @param {Array} items - 队列数据数组
     */
    setData(items) {
        this.items = items || [];
        this.buildPages();
        this.render();
        this.startAuto();
    }

    /**
     * 构建分页数据
     */
    buildPages() {
        this.pages = [];
        if (!this.items.length) return;
        for (let i = 0; i < this.items.length; i += this.pageSize) {
            this.pages.push(this.items.slice(i, i + this.pageSize));
        }
    }

    /**
     * 渲染轮播内容
     */
    render() {
        if (!this.track) return;

        this.track.innerHTML = '';

        if (this.pages.length === 0) {
            const emptyPage = document.createElement('div');
            emptyPage.className = 'queue-page';
            emptyPage.innerHTML = '<div class="empty-queue">暂无等待队列</div>';
            this.track.appendChild(emptyPage);
            this.currentPage = 0;
            this.updateDotsAndArrows();
            this.updateTransform();
            return;
        }

        for (let pageIdx = 0; pageIdx < this.pages.length; pageIdx++) {
            const pageDiv = document.createElement('div');
            pageDiv.className = 'queue-page';
            const itemsPage = this.pages[pageIdx];
            itemsPage.forEach(item => {
                const queueDiv = document.createElement('div');
                queueDiv.className = 'queue-item';
                queueDiv.innerHTML = `
                    <div class="queue-info">
                        <span class="queue-number">${escapeHtml(item.queue_number)}</span>
                        <span class="patient-name">${escapeHtml(item.patient_name || '患者')}</span>
                    </div>
                    <span class="queue-time">${formatTime(item.create_time)}</span>
                `;
                pageDiv.appendChild(queueDiv);
            });
            this.track.appendChild(pageDiv);
        }

        if (this.currentPage >= this.pages.length) this.currentPage = 0;
        this.updateDotsAndArrows();
        this.updateTransform();
    }

    /**
     * 更新指示点和箭头状态
     */
    updateDotsAndArrows() {
        if (!this.dotsContainer) return;

        this.dotsContainer.innerHTML = '';
        const total = this.pages.length;
        const showControls = total > 1;

        if (this.prevBtn) this.prevBtn.style.visibility = showControls ? 'visible' : 'hidden';
        if (this.nextBtn) this.nextBtn.style.visibility = showControls ? 'visible' : 'hidden';

        if (total <= 1) {
            this.dotsContainer.style.display = 'none';
            return;
        }

        this.dotsContainer.style.display = 'flex';
        for (let i = 0; i < total; i++) {
            const dot = document.createElement('div');
            dot.className = `queue-dot ${i === this.currentPage ? 'active' : ''}`;
            dot.addEventListener('click', (e) => {
                e.stopPropagation();
                this.stopAuto();
                this.goToPage(i);
                this.startAuto();
            });
            this.dotsContainer.appendChild(dot);
        }
    }

    /**
     * 更新轨道位置
     */
    updateTransform() {
        if (this.track && this.pages.length > 0) {
            const offset = -this.currentPage * 100;
            this.track.style.transform = `translateX(${offset}%)`;
        }
    }

    /**
     * 跳转到指定页
     * @param {number} index - 页码索引
     */
    goToPage(index) {
        if (index < 0) index = 0;
        if (index >= this.pages.length) index = this.pages.length - 1;
        if (index === this.currentPage) return;
        this.currentPage = index;
        this.updateTransform();
        this.updateDotsAndArrows();
    }

    /**
     * 下一页
     */
    nextPage() {
        if (this.pages.length > 1) {
            this.goToPage((this.currentPage + 1) % this.pages.length);
        }
    }

    /**
     * 上一页
     */
    prevPage() {
        if (this.pages.length > 1) {
            this.goToPage((this.currentPage - 1 + this.pages.length) % this.pages.length);
        }
    }

    /**
     * 开始自动轮播
     */
    startAuto() {
        if (this.timer) clearInterval(this.timer);
        if (this.pages.length > 1 && !this.isHovering) {
            this.timer = setInterval(() => this.nextPage(), this.autoIntervalMs);
        }
    }

    /**
     * 停止自动轮播
     */
    stopAuto() {
        if (this.timer) {
            clearInterval(this.timer);
            this.timer = null;
        }
    }

    /**
     * 销毁轮播实例
     */
    destroy() {
        this.stopAuto();
        if (this.container) this.container.innerHTML = '';
    }
}

// ======================== 过号记录轮播功能 ========================

/**
 * 分页过号记录数据
 * @param {Array} patients - 过号患者数据数组
 * @returns {Array} 分页后的页面数组
 */
function paginateSkipped(patients) {
    let pages = [];
    const PAGE_SIZE = 10;   // 改为 10
    for (let i = 0; i < patients.length; i += PAGE_SIZE) {
        pages.push(patients.slice(i, i + PAGE_SIZE));
    }
    return pages;
}

/**
 * 渲染过号记录轮播
 */
function renderSkippedCarousel() {
    const track = document.getElementById('skippedTrack');
    if (!track) return;

    const pages = paginateSkipped(skippedPatients);
    totalPages = pages.length;
    track.innerHTML = '';

    if (totalPages === 0) {
        track.innerHTML = '<div class="card-page"><div class="empty-state" style="grid-column:1/-1;">暂无过号记录</div></div>';
        currentPageIndex = 0;
        updateSkippedTrackTransform();
        updateSkippedDots();
        return;
    }

    pages.forEach(p => {
        const pageDiv = document.createElement('div');
        pageDiv.className = 'card-page';
        for (let i = 0; i < 10; i++) {   // 改为 10
            if (p[i]) {
                const card = document.createElement('div');
                card.className = 'skipped-card';
                card.innerHTML = `
                    <span class="skipped-number">${escapeHtml(p[i].queue_number)}</span>
                    <span class="skipped-patient">${escapeHtml(p[i].patient_name || '患者')}</span>
                    <span class="skipped-business">${escapeHtml(p[i].business_name || '')}</span>
                    <span class="skipped-time">${formatTime(p[i].skip_time)}</span>
                `;
                pageDiv.appendChild(card);
            } else {
                const ph = document.createElement('div');
                ph.style.visibility = 'hidden';
                pageDiv.appendChild(ph);
            }
        }
        track.appendChild(pageDiv);
    });

    if (currentPageIndex >= totalPages) currentPageIndex = 0;
    updateSkippedTrackTransform();
    updateSkippedDots();

    const prevBtn = document.getElementById('prevPageBtn');
    const nextBtn = document.getElementById('nextPageBtn');

    if (totalPages <= 1) {
        if (prevBtn) prevBtn.style.visibility = 'hidden';
        if (nextBtn) nextBtn.style.visibility = 'hidden';
        stopAutoScroll();
    } else {
        if (prevBtn) prevBtn.style.visibility = 'visible';
        if (nextBtn) nextBtn.style.visibility = 'visible';
        startAutoScroll();
    }
}

/**
 * 更新过号轨道位置
 */
function updateSkippedTrackTransform() {
    const track = document.getElementById('skippedTrack');
    if (track) {
        track.style.transform = `translateX(-${currentPageIndex * 100}%)`;
    }
}

/**
 * 更新过号指示点
 */
function updateSkippedDots() {
    const dotsDiv = document.getElementById('carouselDots');
    if (!dotsDiv) return;

    dotsDiv.innerHTML = '';
    for (let i = 0; i < totalPages; i++) {
        const dot = document.createElement('div');
        dot.className = `dot ${i === currentPageIndex ? 'active' : ''}`;
        dot.addEventListener('click', () => {
            stopAutoScroll();
            currentPageIndex = i;
            updateSkippedTrackTransform();
            updateSkippedDots();
            startAutoScroll();
        });
        dotsDiv.appendChild(dot);
    }
}

/**
 * 下一页
 */
function nextPage() {
    if (totalPages > 0) {
        currentPageIndex = (currentPageIndex + 1) % totalPages;
        updateSkippedTrackTransform();
        updateSkippedDots();
    }
}

/**
 * 上一页
 */
function prevPage() {
    if (totalPages > 0) {
        currentPageIndex = (currentPageIndex - 1 + totalPages) % totalPages;
        updateSkippedTrackTransform();
        updateSkippedDots();
    }
}

/**
 * 开始过号自动轮播
 */
function startAutoScroll() {
    if (carouselInterval) clearInterval(carouselInterval);
    if (totalPages > 1) {
        carouselInterval = setInterval(nextPage, CAROUSEL_INTERVAL_MS);
    }
}

/**
 * 停止过号自动轮播
 */
function stopAutoScroll() {
    if (carouselInterval) {
        clearInterval(carouselInterval);
        carouselInterval = null;
    }
}

/**
 * 添加过号患者记录
 * @param {Object} data - 过号数据
 */
function addSkippedPatient(data) {
    const newItem = {
        queue_number: data.queue_number,
        patient_name: data.patient_name || '患者',
        business_name: data.business_name || '',
        skip_time: data.skip_time || new Date().toISOString()
    };
    if (!skippedPatients.some(p => p.queue_number === newItem.queue_number)) {
        skippedPatients.unshift(newItem);
        if (skippedPatients.length > 150) skippedPatients.pop();
        renderSkippedCarousel();
        document.getElementById('skippedCount').innerText = skippedPatients.length;
    }
}

/**
 * 更新过号计数
 */
function updateSkippedCount() {
    const badge = document.getElementById('skippedCount');
    if (badge) badge.textContent = skippedPatients.length;
}

// ======================== API交互与数据更新 ========================

/**
 * 加载业务类型配置
 */
async function loadBusinessTypes() {
    try {
        const resp = await fetch(`${API_BASE}/business-types`);
        if (resp.ok) {
            businessTypes = await resp.json();
        }
    } catch (e) {
        console.warn('加载业务类型失败:', e);
    }
}

/**
 * 加载显示数据
 */
async function loadDisplayData() {
    try {
        const resp = await fetch(`${API_BASE}/api/queue/status`);
        if (resp.ok) {
            const data = await resp.json();
            updateDisplay(data);
        }
    } catch (e) {
        console.warn('加载显示数据失败:', e);
    }
}

/**
 * 更新显示数据
 * @param {Object} data - 显示数据对象
 */
function updateDisplay(data) {
    updateCurrentCalls(data.current_calls);
    updateBusinessBoards(data.business_status);
}

/**
 * 更新当前叫号
 * @param {Array} calls - 叫号数据数组
 */
function updateCurrentCalls(calls) {
    currentCallsData = calls && calls.length ? calls : [];
    renderCallsCarousel();
}

/**
 * 更新业务窗口
 * @param {Object} businessStatus - 业务状态数据
 */
function updateBusinessBoards(businessStatus) {
    const container = document.getElementById('businessBoards');
    if (!businessTypes || Object.keys(businessTypes).length === 0) {
        container.innerHTML = '<div class="loading-state">加载业务配置...</div>';
        return;
    }

    // 销毁旧的轮播实例
    for (let carousel of boardCarousels.values()) {
        carousel.destroy();
    }
    boardCarousels.clear();

    container.innerHTML = Object.entries(businessTypes).map(([type, biz]) => {
        const status = businessStatus[type] || { waiting_count: 0 };
        return `
            <div class="board">
                <div class="board-header" style="background: linear-gradient(135deg, ${biz.color} 0%, ${darkenColor(biz.color)} 100%);">
                    <div class="board-title">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <rect x="3" y="3" width="18" height="18" rx="2"/>
                        </svg>
                        ${biz.name}
                    </div>
                    <div class="waiting-count">等待 <strong>${status.waiting_count}</strong> 人</div>
                </div>
                <div class="queue-carousel-container" id="queueBoard_${type}"></div>
            </div>
        `;
    }).join('');

    // 创建新的轮播实例
    Object.keys(businessTypes).forEach(type => {
        const boardContainer = document.getElementById(`queueBoard_${type}`);
        if (boardContainer) {
            const carousel = new QueueBoardCarousel(boardContainer, type, 5, 4500);
            boardCarousels.set(type, carousel);
            loadQueueList(type);
        }
    });
}

/**
 * 加载队列列表
 * @param {string} businessId - 业务ID
 */
async function loadQueueList(businessId) {
    try {
        const resp = await fetch(`${API_BASE}/api/queue/list?business_id=${businessId}&status=waiting`);
        if (resp.ok) {
            const data = await resp.json();
            const carousel = boardCarousels.get(businessId);
            if (carousel) carousel.setData(data.queues || []);
        }
    } catch (e) {
        console.error('加载队列列表失败:', e);
    }
}

// ======================== WebSocket与公告功能 ========================

/**
 * 添加公告消息
 * @param {string} msg - 公告消息内容
 */
function addAnnouncement(msg) {
    const annDiv = document.getElementById('announcementMsg');
    if (annDiv) {
        annDiv.innerText = `🔔 ${msg}`;
        annDiv.style.animation = 'none';
        setTimeout(() => {
            annDiv.style.animation = 'scroll 25s linear infinite';
        }, 10);
        // 5秒后恢复默认公告
        setTimeout(() => {
            if (annDiv) annDiv.innerText = '🔔 请在等候区稍候，注意听语音叫号，过号请到服务台重新激活';
        }, 5000);
    }
}

/**
 * 初始化WebSocket连接
 */
function initWebSocket() {
    ws = new WebSocket(`${WS_URL}/ws/display`);

    ws.onopen = () => {
        console.log('WebSocket连接成功');
    };

    ws.onmessage = (e) => {
        try {
            const data = JSON.parse(e.data);
            switch (data.type) {
                case 'init':
                    updateDisplay(data.data);
                    break;
                case 'call':
                    addAnnouncement(`请 ${data.data.queue_number} 号到 ${data.data.window_name} 办理`);
//                    loadDisplayData();
                    break;
                case 'queue_update':
//                    loadDisplayData();
                    break;
                case 'complete':
//                    loadDisplayData();
                    break;
                case 'skip':
                    addAnnouncement(`${data.data.queue_number} 号已过号，请重新取号`);
                    addSkippedPatient(data.data);
//                    loadDisplayData();
                    break;
                case 'reactivate':
                    addAnnouncement(`${data.data.queue_number} 号已重新激活`);
//                    loadDisplayData();
                    break;
            }
        } catch (err) {
            console.error('解析WebSocket消息失败:', err);
        }
    };

    ws.onclose = () => {
        // 3秒后重连
        setTimeout(initWebSocket, 3000);
    };

    ws.onerror = (err) => {
        console.warn('WebSocket错误:', err);
    };
}

/**
 * 启动时钟
 */
function startClock() {
    const update = () => {
        const now = new Date();
        document.getElementById('currentDate').innerText = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
        document.getElementById('currentTime').innerText = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;
    };
    update();
    setInterval(update, 60000);
}

/**
 * 绑定交互事件
 */
function bindEvents() {
    document.getElementById('prevPageBtn')?.addEventListener('click', () => {
        stopAutoScroll();
        prevPage();
        startAutoScroll();
    });

    document.getElementById('nextPageBtn')?.addEventListener('click', () => {
        stopAutoScroll();
        nextPage();
        startAutoScroll();
    });

    document.getElementById('callsPrevBtn')?.addEventListener('click', () => {
        stopCallsAutoScroll();
        prevCallsPage();
        startCallsAutoScroll();
    });

    document.getElementById('callsNextBtn')?.addEventListener('click', () => {
        stopCallsAutoScroll();
        nextCallsPage();
        startCallsAutoScroll();
    });

    const carouselDiv = document.querySelector('.skipped-carousel');
    if (carouselDiv) {
        carouselDiv.addEventListener('mouseenter', stopAutoScroll);
        carouselDiv.addEventListener('mouseleave', startAutoScroll);
    }

    bindCallsCarouselHover();
}

/**
 * 加载过号历史记录
 */
async function loadSkippedHistory() {
    try {
        const resp = await fetch(`${API_BASE}/api/queue/overdue`);
        if (resp.ok) {
            const data = await resp.json();
            skippedPatients = data.list || [];
        } else {
            skippedPatients = [];
        }
    } catch (e) {
        skippedPatients = [];
    }
    renderSkippedCarousel();
    updateSkippedCount();
}

/**
 * 初始化应用
 */
async function init() {
    await loadBusinessTypes();
    await loadDisplayData();
    await loadSkippedHistory();
    initWebSocket();
    startClock();
    bindEvents();
    // 每10秒刷新一次数据
    setInterval(loadDisplayData, 10000);

    // 在 init 函数末尾添加
    document.getElementById('fullscreenTrigger').addEventListener('click', function() {
        if (!document.fullscreenElement && !document.webkitFullscreenElement) {
            const elem = document.documentElement;
            if (elem.requestFullscreen) elem.requestFullscreen();
            else if (elem.webkitRequestFullscreen) elem.webkitRequestFullscreen();
            else if (elem.msRequestFullscreen) elem.msRequestFullscreen();
        } else {
            if (document.exitFullscreen) document.exitFullscreen();
            else if (document.webkitExitFullscreen) document.webkitExitFullscreen();
            else if (document.msExitFullscreen) document.msExitFullscreen();
        }
    });
}

// ======================== 页面加载与卸载事件 ========================

window.addEventListener('DOMContentLoaded', init);

window.addEventListener('beforeunload', () => {
    // 关闭WebSocket连接
    if (ws) ws.close();

    // 销毁所有轮播实例
    for (let c of boardCarousels.values()) {
        c.destroy();
    }

    // 清除定时器
    if (carouselInterval) clearInterval(carouselInterval);
    stopCallsAutoScroll();
});

// ======================== Service Worker注册 ========================
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js').then(reg => {
            console.log('Service Worker 注册成功', reg);
        }).catch(err => {
            console.log('Service Worker 注册失败', err);
        });
    });
}
