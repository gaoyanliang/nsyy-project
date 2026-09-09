(function() {
    // =========================================================
    // 第一部分：语音转写功能（完整保留，仅适配UI变化）
    // =========================================================
    function getApiConfig() {
        const host = window.location.hostname;
        const portMap = {
            'oa.nsyy.com.cn': 6080,
            '192.168.3.12':   6083,
            '192.168.124.9':  8081,
            '127.0.0.1':      8081,
            'localhost':      8081,
        };
        let port = portMap[host] || 8081;
        if (host === 'oa.nsyy.com.cn') {
            return { apiBase: `https://${host}:6081/mz`, wsUrl: `wss://${host}:6081/mz` };
        }
        if (host === '192.168.3.12') {
            return { apiBase: `https://${host}:6083/mz`, wsUrl: `wss://${host}:6083/mz` };
        }
        return { apiBase: `http://${host}:${port}/mz`, wsUrl: `ws://${host}:${port}/mz` };
    }
    const config = getApiConfig();
    const API_BASE = config.apiBase;
    const WS_URL = config.wsUrl;

    // ---- DOM 元素 ----
    const $ = (sel) => document.querySelector(sel);
    const startBtn = $('#startBtn');
    const stopBtn = $('#stopBtn');
    const voiceTimer = $('#voiceTimer');
    const voiceHint = $('#voiceHint');
    const voiceLiveText = $('#voiceLiveText');
    const recordingBadge = $('#recordingBadgeCompact');
    const wsStatusBadge = $('#wsStatusBadge');
    const voiceStatusBadge = $('#voiceStatusBadge');
    const errorMsg = $('#errorMsg');
    const btnClear = $('#btnClear');
    const btnCopy = $('#btnCopy');
    const wordCountEl = $('#wordCount');
    const sentenceCountEl = $('#sentenceCount');
    const examFindingsTextarea = $('#examFindings');

    // ---- 状态 ----
    let ws = null;
    let mediaStream = null;
    let audioContext = null;
    let source = null;
    let processor = null;
    let isRecording = false;
    let isConnected = false;
    let fullText = '';
    let currentStash = '';
    let sentenceCountVal = 0;
    let heartbeatInterval = null;
    let connectionStatus = 'disconnected';
    const SAMPLE_RATE = 16000;
    const CHUNK_SIZE = 4096;

    let mediaRecorder = null;
    let audioChunks = [];

    // ---- 本地暂存 ----
    const STORAGE_KEY = 'medical_asr_report_draft';
    function saveDraft() {
        const draft = { examFindings: examFindingsTextarea.value, updatedAt: Date.now() };
        try { localStorage.setItem(STORAGE_KEY, JSON.stringify(draft)); } catch (e) {}
    }
    function loadDraft() {
        try {
            const raw = localStorage.getItem(STORAGE_KEY);
            if (!raw) return false;
            const draft = JSON.parse(raw);
            if (draft.examFindings) {
                examFindingsTextarea.value = draft.examFindings;
                fullText = draft.examFindings;
                updateWordCount();
                updateSentenceCount();
            }
            return true;
        } catch (e) { return false; }
    }
    function clearDraft() { localStorage.removeItem(STORAGE_KEY); }

    let saveTimeout;
    function debouncedSave() {
        clearTimeout(saveTimeout);
        saveTimeout = setTimeout(saveDraft, 300);
    }
    examFindingsTextarea.addEventListener('input', function() {
        updateWordCount();
        updateSentenceCount();
        debouncedSave();
        fullText = this.value;
    });


    // ---- Toast ----
    function showToast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = 'toast ' + type;
        const icons = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' };
        toast.textContent = (icons[type] || '') + ' ' + message;
        container.appendChild(toast);
        setTimeout(() => {
            if (toast.parentNode) {
                toast.classList.add('removing');
                toast.addEventListener('animationend', () => toast.remove());
            }
        }, 3000);
    }

    // ---- 连接管理 ----
    function setConnectionStatus(status) {
        connectionStatus = status;
        const badge = wsStatusBadge;
        badge.className = 'header-badge';
        if (status === 'connected') {
            badge.classList.add('online');
            badge.innerHTML = '<span class="dot"></span> 服务已连接';
            voiceHint.textContent = '点击麦克风开始语音录入';
        } else if (status === 'connecting') {
            badge.classList.add('online');
            badge.innerHTML = '<span class="dot"></span> 连接中...';
            voiceHint.textContent = '正在连接语音服务，请稍候...';
        } else {
            badge.classList.add('offline');
            badge.innerHTML = '<span class="dot"></span> 未连接';
            voiceHint.textContent = '未连接，点击麦克风建立连接';
        }
    }

    async function connect() {
        if (isConnected || connectionStatus === 'connecting') return;
        setConnectionStatus('connecting');
        const wsUrl = `${WS_URL}/asr/ws/transcribe`;
        try {
            ws = new WebSocket(wsUrl);
            ws.onopen = () => {
                isConnected = true;
                setConnectionStatus('connected');
                startBtn.disabled = false;
                stopBtn.disabled = true;
                showError('');
                console.log('WebSocket 连接成功');
            };
            ws.onmessage = (event) => { handleMessage(event.data); };
            ws.onclose = () => {
                isConnected = false;
                setConnectionStatus('disconnected');
                startBtn.disabled = false;
                stopBtn.disabled = true;
                if (isRecording) stopRecording();
                showToast('语音服务连接已断开，请点击麦克风重新连接', 'warning');
            };
            ws.onerror = (error) => {
                console.error('WebSocket 错误:', error);
                setConnectionStatus('disconnected');
                showError('WebSocket 连接错误，请检查网络');
                showToast('连接失败，请刷新页面或稍后重试', 'error');
            };
        } catch (err) {
            console.error('连接失败:', err);
            setConnectionStatus('disconnected');
            showToast('连接失败：' + err.message, 'error');
        }
    }

    // ---- 消息处理 ----
    function handleMessage(rawData) {
        try {
            const data = JSON.parse(rawData);
            const type = data.type;
            switch (type) {
                case 'stash': {
                    const delta = data.text || '';
                    if (delta) {
                        currentStash += delta;
                        updateLiveTextWithTyping(currentStash);
                    }
                    break;
                }
                case 'final': {
                    const text = data.text || '';
                    if (text.trim()) {
                        currentStash = '';
                        fullText += text;
                        if (!text.endsWith('。') && !text.endsWith('！') && !text.endsWith('？')) {
                            fullText += '。';
                        }
                        sentenceCountVal++;
                        sentenceCountEl.textContent = sentenceCountVal;

                        let currentVal = examFindingsTextarea.value;
                        if (currentVal.length > 0 && !'。！？'.includes(currentVal.slice(-1))) {
                            examFindingsTextarea.value = currentVal + '。' + text;
                        } else {
                            examFindingsTextarea.value = currentVal + text;
                        }
                        examFindingsTextarea.dispatchEvent(new Event('input'));
                        updateWordCount();
                        examFindingsTextarea.scrollTop = examFindingsTextarea.scrollHeight;
                        voiceLiveText.innerHTML = '';
                        voiceLiveText.classList.remove('active');
                    }
                    break;
                }
                case 'speech_start': {
                    setRecordingUI(true);
                    recordingBadge.textContent = '录音中...';
                    recordingBadge.className = 'recording-badge-compact recording';
                    voiceStatusBadge.className = 'header-badge recording';
                    voiceStatusBadge.innerHTML = '<span class="dot"></span> 录音中';
                    break;
                }
                case 'speech_stop': {
                    recordingBadge.textContent = '录入完成';
                    recordingBadge.className = 'recording-badge-compact';
                    voiceStatusBadge.className = 'header-badge online';
                    voiceStatusBadge.innerHTML = '<span class="dot"></span> 语音就绪';
                    break;
                }
                case 'error': {
                    const errText = data.text || 'ASR 服务错误';
                    if (errText.includes('180')) {
                        showError('超180秒没有语音输入，连接已断开，请重新点击麦克风使用');
                    } else {
                        showError(errText);
                    }
                    if (errText.includes('response_idle_timeout')) {
                        showToast('语音服务因长时间无操作已断开，请重新点击麦克风', 'warning');
                        if (ws && ws.readyState === WebSocket.OPEN) {
                            ws.close(1000, '空闲超时');
                        }
                    }
                    break;
                }
                case 'pong': break;
            }
        } catch (err) {
            console.error('解析消息失败:', err);
        }
    }

    // ---- UI 辅助 ----
    function updateLiveTextWithTyping(text) {
        if (!text) {
            voiceLiveText.innerHTML = '实时听写预览...';
            voiceLiveText.classList.remove('active');
            return;
        }
        voiceLiveText.classList.add('active');
        voiceLiveText.innerHTML = escapeHtml(text) + '<span class="typing-cursor"></span>';
    }

    function showError(msg) {
        if (!msg) { errorMsg.classList.remove('show'); return; }
        errorMsg.textContent = msg;
        errorMsg.className = 'error-msg show';
    }

    function updateWordCount() {
        const text = examFindingsTextarea.value;
        wordCountEl.textContent = text.replace(/\s/g, '').length;
    }
    function updateSentenceCount() {
        const text = examFindingsTextarea.value;
        const sentences = text.split(/[。！？\n]/).filter(s => s.trim().length > 0);
        sentenceCountEl.textContent = sentences.length;
        sentenceCountVal = sentences.length;
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function setRecordingUI(recording) {
        if (recording) {
            startBtn.classList.add('recording');
            stopBtn.disabled = false;
            voiceHint.textContent = '正在录音，点击停止按钮结束';
        } else {
            startBtn.classList.remove('recording');
            stopBtn.disabled = true;
            voiceHint.textContent = '点击麦克风开始语音录入';
            voiceLiveText.innerHTML = '实时听写预览...';
            voiceLiveText.classList.remove('active');
        }
    }

    // ---- 录音核心 ----
    async function startRecording() {
        console.log('[DEBUG] startRecording called');
        if (isRecording) {
            console.log('[DEBUG] Already recording, return');
            return;
        }
        const isWsAlive = isConnected && ws && ws.readyState === WebSocket.OPEN;
        if (!isWsAlive) {
            console.log('[DEBUG] WebSocket not alive, reconnecting...');
            if (ws) { try { ws.close(); } catch (e) {} ws = null; }
            isConnected = false;
            setConnectionStatus('disconnected');
            await connect();
            let waitCount = 0;
            while (!isConnected && waitCount < 30) {
                await new Promise(resolve => setTimeout(resolve, 100));
                waitCount++;
            }
            if (!isConnected) {
                showToast('❌ 无法连接语音服务，请稍后重试', 'error');
                console.log('[DEBUG] WebSocket connection failed');
                return;
            }
        }
        try {
            console.log('[DEBUG] Requesting getUserMedia...');
            mediaStream = await navigator.mediaDevices.getUserMedia({
                audio: { sampleRate: SAMPLE_RATE, channelCount: 1, echoCancellation: true, noiseSuppression: true }
            });
            console.log('[DEBUG] getUserMedia success, stream:', mediaStream);

            // 确保 UI 更新在下一帧
            requestAnimationFrame(() => {
                isRecording = true;
                startBtn.disabled = true;
                stopBtn.disabled = false;
                setRecordingUI(true);
                voiceStatusBadge.className = 'header-badge recording';
                voiceStatusBadge.innerHTML = '<span class="dot"></span> 录音中';
            });

            // 媒体录制器（可选，用于保存录音）
            mediaRecorder = new MediaRecorder(mediaStream);
            audioChunks = [];
            mediaRecorder.ondataavailable = (e) => { if (e.data.size > 0) audioChunks.push(e.data); };
            mediaRecorder.onstop = () => {
                const blob = new Blob(audioChunks, { type: 'audio/webm' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                let patientName = document.getElementById('pName')?.textContent.trim() || '未知患者';
                const cleanName = patientName.replace(/[\\/:*?"<>|]/g, '');
                const now = new Date();
                const pad = (n) => String(n).padStart(2, '0');
                const localTime = `${now.getFullYear()}${pad(now.getMonth()+1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
                a.download = `录音_${cleanName}_${localTime}.webm`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
                audioChunks = [];
            };
            mediaRecorder.start();

            audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: SAMPLE_RATE });
            const audioSource = audioContext.createMediaStreamSource(mediaStream);
            const audioProcessor = audioContext.createScriptProcessor(CHUNK_SIZE, 1, 1);
            audioSource.connect(audioProcessor);
            audioProcessor.connect(audioContext.destination);

            audioProcessor.onaudioprocess = (e) => {
                if (!isRecording || !isConnected) return;
                const inputData = e.inputBuffer.getChannelData(0);
                const pcmData = float32ToInt16(inputData);
                const base64Data = arrayBufferToBase64(pcmData);
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({ type: 'audio', data: base64Data }));
                }
            };
            processor = audioProcessor;
            source = audioSource;
            console.log('🎤 开始录音');
            startTimer();
            heartbeatInterval = setInterval(() => {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.send(JSON.stringify({ type: 'ping' }));
                }
            }, 15000);
        } catch (err) {
            console.error('启动录音失败:', err);
            showError('麦克风启动失败: ' + err.message);
            startBtn.disabled = false;
            stopBtn.disabled = true;
            setRecordingUI(false);
            isRecording = false;
        }
    }

    async function stopRecording() {
        if (!isRecording) return;
        isRecording = false;
        startBtn.disabled = false;
        stopBtn.disabled = true;
        setRecordingUI(false);
        voiceStatusBadge.className = 'header-badge online';
        voiceStatusBadge.innerHTML = '<span class="dot"></span> 语音就绪';
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'commit' }));
        }
        if (processor) { processor.disconnect(); processor = null; }
        if (source) { source.disconnect(); source = null; }
        if (audioContext) { await audioContext.close(); audioContext = null; }
        if (mediaStream) { mediaStream.getTracks().forEach(track => track.stop()); mediaStream = null; }
        console.log('⏹️ 停止录音');
        stopTimer();
        recordingBadge.textContent = '录入完成';
        recordingBadge.className = 'recording-badge-compact';
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            mediaRecorder.stop();
        }
        if (heartbeatInterval) { clearInterval(heartbeatInterval); heartbeatInterval = null; }
    }

    // ---- 计时器 ----
    let recordingStartTime = null, timerInterval = null;
    function startTimer() {
        stopTimer();
        recordingStartTime = Date.now();
        updateTimerDisplay();
        timerInterval = setInterval(updateTimerDisplay, 200);
    }
    function stopTimer() {
        if (timerInterval) { clearInterval(timerInterval); timerInterval = null; }
        voiceTimer.textContent = '00:00';
    }
    function updateTimerDisplay() {
        if (!recordingStartTime) return;
        const elapsed = Math.floor((Date.now() - recordingStartTime) / 1000);
        voiceTimer.textContent = String(Math.floor(elapsed / 60)).padStart(2, '0') + ':' + String(elapsed % 60).padStart(2, '0');
    }

    // ---- 音频工具 ----
    function float32ToInt16(float32Array) {
        const int16Array = new Int16Array(float32Array.length);
        for (let i = 0; i < float32Array.length; i++) {
            const s = Math.max(-1, Math.min(1, float32Array[i]));
            int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }
        return int16Array;
    }
    function arrayBufferToBase64(buffer) {
        const bytes = new Uint8Array(buffer.buffer);
        let binary = '';
        for (let i = 0; i < bytes.byteLength; i++) binary += String.fromCharCode(bytes[i]);
        return btoa(binary);
    }

    // ---- 事件绑定 ----
    startBtn.addEventListener('click', () => { if (!isRecording) startRecording(); });
    stopBtn.addEventListener('click', () => { if (isRecording) stopRecording(); });
    btnClear.addEventListener('click', function() {
        examFindingsTextarea.value = '';
        fullText = '';
        currentStash = '';
        sentenceCountVal = 0;
        sentenceCountEl.textContent = '0';
        updateWordCount();
        clearDraft();
        showToast('转写内容已清空', 'info');
    });
    btnCopy.addEventListener('click', function() {
        const text = examFindingsTextarea.value;
        if (text.trim()) {
            navigator.clipboard.writeText(text).then(() => showToast('✅ 已复制到剪贴板', 'success'))
                .catch(() => showToast('复制失败，请手动复制', 'error'));
        }
    });
    document.addEventListener('keydown', function(e) {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') return;
        if (e.code === 'Space' && !e.ctrlKey && !e.metaKey && !e.altKey) {
            e.preventDefault();
            if (isRecording) stopRecording();
            else startRecording();
        }
    });

    // ---- 初始化语音 ----
    function initVoice() {
        const hasDraft = loadDraft();
        if (hasDraft) showToast('已恢复上次暂存的数据', 'info');
        startBtn.disabled = false;
        stopBtn.disabled = true;
        setConnectionStatus('disconnected');
        updateWordCount();
        updateSentenceCount();
        console.log('语音转写初始化完成');

        // ===== 将录音控制暴露给全局，供外部（Python）调用 =====
        window.startRecording = startRecording;
        window.stopRecording = stopRecording;
        window.toggleRecording = function() {
            if (isRecording) {
                stopRecording();
            } else {
                startRecording();
            }
        };
        // 如果需要读取录音状态，可以暴露一个函数
        window.isRecording = function() { return isRecording; };
    }
    initVoice();

    // =========================================================
    // 第二部分：报告模块（含历史互斥逻辑）
    // =========================================================
    (function() {
        // ---- DOM 引用 ----
        const zhuyuanhaoInput = document.getElementById('zhuyuanhaoInput');
        const queryBtn = document.getElementById('queryPatientBtn');
        const patientInfoArea = document.getElementById('patientInfoArea');
        const pName = document.getElementById('pName');
        const pSex = document.getElementById('pSex');
        const pAge = document.getElementById('pAge');
        const pDept = document.getElementById('pDept');
        const checkItemsContainer = document.getElementById('checkItemsContainer');
        const submitBtn = document.getElementById('submitBtn');
        const reportTableBody = document.getElementById('reportTableBody');
        const paginationControls = document.getElementById('paginationControls');
        const refreshListBtn = document.getElementById('refreshListBtn');
        const loadingOverlay = document.getElementById('loadingOverlay');
        const cancelEditBtn = document.getElementById('cancelEditBtn');
        const editModeBadge = document.getElementById('editModeBadge');
        const reportPanel = document.getElementById('reportPanel');

        const modalOverlay = document.getElementById('reportModal');
        const modalCloseBtn = document.getElementById('modalCloseBtn');
        const modalTitle = document.getElementById('modalTitle');
        const modalDetailContent = document.getElementById('modalDetailContent');
        const copyReportBtnHeader = document.getElementById('copyReportBtnHeader');

        // ---- 状态 ----
        let currentPatient = null;
        let selectedCheckItem = null;
        let selectedYizhuid = null;
        let currentPage = 1;
        const PAGE_SIZE = 5;

        let isEditMode = false;
        let editingRecordId = null;
        let editingRecordData = null;
        let beforeEditFullText = '';
        let beforeEditExamFindings = '';

        // ---- 工具函数 ----
        function showToastPacs(message, type = 'info') {
            // 移除可能存在的旧 toast（避免堆积）
            const oldToasts = document.querySelectorAll('.custom-toast-item');
            oldToasts.forEach(t => t.remove());

            // 创建 toast 元素
            const toast = document.createElement('div');
            toast.className = 'custom-toast-item';
            const icons = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' };
            const icon = icons[type] || 'ℹ️';
            toast.textContent = icon + ' ' + message;

            // ★★★ 强制内联样式，使用 !important 确保覆盖 ★★★
            toast.style.cssText = `
                position: fixed !important;
                top: 20px !important;
                right: 20px !important;
                z-index: 9999999 !important;
                background: #333 !important;
                color: #fff !important;
                padding: 12px 20px !important;
                border-radius: 8px !important;
                box-shadow: 0 4px 20px rgba(0,0,0,0.3) !important;
                font-size: 0.9rem !important;
                font-weight: 500 !important;
                max-width: 380px !important;
                pointer-events: none !important;
                opacity: 1 !important;
                transition: opacity 0.3s !important;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif !important;
            `;
            // 根据类型设置背景色
            const bgColors = {
                success: '#2d8a56',
                error: '#d14343',
                info: '#1a6fb5',
                warning: '#c0792b'
            };
            toast.style.background = (bgColors[type] || '#333') + ' !important';

            // 添加到 body（确保在顶层）
            document.body.appendChild(toast);

            // 自动移除（3.5 秒后）
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.style.opacity = '0 !important';
                    setTimeout(() => {
                        if (toast.parentNode) toast.remove();
                    }, 300);
                }
            }, 3500);
        }

        function showLoading(show) {
            loadingOverlay.style.display = show ? 'flex' : 'none';
        }

        function showConfirmDialog(title, message) {
            return new Promise((resolve) => {
                // 移除可能已存在的旧确认弹窗
                const oldModal = document.querySelector('.custom-confirm-overlay');
                if (oldModal) oldModal.remove();

                // 创建覆盖层
                const overlay = document.createElement('div');
                overlay.className = 'custom-confirm-overlay';
                overlay.style.cssText = `
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100vw;
                    height: 100vh;
                    background: rgba(0,0,0,0.5);
                    z-index: 999999;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    backdrop-filter: blur(2px);
                `;
                // 点击背景不关闭，防止误触

                // 弹窗盒子
                const box = document.createElement('div');
                box.style.cssText = `
                    background: #ffffff;
                    border-radius: 14px;
                    max-width: 450px;
                    width: 90%;
                    padding: 24px 20px 20px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    text-align: center;
                `;

                // 图标
                const icon = document.createElement('div');
                icon.textContent = '⚠️';
                icon.style.cssText = 'font-size:2.2rem; margin-bottom:10px;';
                box.appendChild(icon);

                // 标题
                const titleEl = document.createElement('h3');
                titleEl.textContent = title || '确认操作';
                titleEl.style.cssText = 'font-size:1rem; margin-bottom:6px; color: #1a1d23;';
                box.appendChild(titleEl);

                // 消息
                const msgEl = document.createElement('p');
                msgEl.textContent = message || '确定要执行此操作吗？';
                msgEl.style.cssText = 'font-size:0.9rem; color: #5f6570; margin-bottom:16px; white-space:pre-wrap;';
                box.appendChild(msgEl);

                // 按钮容器
                const btnContainer = document.createElement('div');
                btnContainer.style.cssText = 'display:flex; justify-content:center; gap:10px;';

                const cancelBtn = document.createElement('button');
                cancelBtn.textContent = '取消';
                cancelBtn.className = 'btn btn-outline';
                cancelBtn.style.cssText = 'padding: 6px 16px; border-radius: 6px; border: 1.5px solid #e2e5ea; background: #fff; cursor: pointer; min-width:70px;';

                const okBtn = document.createElement('button');
                okBtn.textContent = '确定';
                okBtn.className = 'btn btn-primary';
                okBtn.style.cssText = 'padding: 6px 16px; border-radius: 6px; border: none; background: #1a6fb5; color: #fff; cursor: pointer; min-width:70px;';

                btnContainer.appendChild(cancelBtn);
                btnContainer.appendChild(okBtn);
                box.appendChild(btnContainer);

                overlay.appendChild(box);
                document.body.appendChild(overlay);

                // 清理函数
                function cleanup() {
                    if (overlay.parentNode) overlay.remove();
                }

                // 事件绑定
                cancelBtn.onclick = function() {
                    cleanup();
                    resolve(false);
                };
                okBtn.onclick = function() {
                    cleanup();
                    resolve(true);
                };
                // 点击覆盖层不关闭，只通过按钮关闭
                overlay.onclick = function(e) {
                    if (e.target === overlay) {
                        // 可选：点击背景不做任何事，防止误触
                        // 或者也可以关闭，根据需求。但用户通常期望点击背景不关闭，所以我们忽略。
                    }
                };
                // 自动聚焦确定按钮
                setTimeout(() => okBtn.focus(), 100);
            });
        }


        // ---- 清除暂存按钮事件绑定 ----
        const clearCacheBtn = document.getElementById('clearCacheBtn');
        if (clearCacheBtn) {
            clearCacheBtn.addEventListener('click', async function() {
                const confirmed = await showConfirmDialog('清除暂存', '确定清除所有本地暂存数据吗？');
                if (confirmed) {
                    clearDraft();
                    examFindingsTextarea.value = '';
                    fullText = '';
                    currentStash = '';
                    sentenceCountVal = 0;
                    sentenceCountEl.textContent = '0';
                    updateWordCount();
                    showToast('暂存数据已清除', 'info');
                }
            });
        }


        function fallbackCopy(text) {
            const textarea = document.createElement('textarea');
            textarea.value = text;
            textarea.style.position = 'fixed';
            textarea.style.opacity = '0';
            textarea.style.left = '-9999px';
            textarea.style.top = '-9999px';
            document.body.appendChild(textarea);
            textarea.select();
            try {
                document.execCommand('copy');
                showToast('已复制', 'success');
            } catch (e) {
                showToast('❌ 复制失败，请手动复制', 'error');
            }
            document.body.removeChild(textarea);
        }


        // ---- 模态框 ----
        let editingRecordIdModal = null;
        let editingField = null;
        let isEditModeModal = false;


        // ===== 全局变量保存动态创建的弹窗元素 =====
        let dynamicModal = null;

        function openModal(title, content, editable = false, recordId = null, field = null, forceText = false) {
            try {
                console.log('[openModal] title:', title);
                console.log('[openModal] content type:', typeof content);

                // 如果已有弹窗，先移除
                if (dynamicModal) {
                    document.body.removeChild(dynamicModal);
                    dynamicModal = null;
                }

                // --- 创建覆盖层 ---
                const overlay = document.createElement('div');
                overlay.style.cssText = `
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100vw;
                    height: 100vh;
                    background: rgba(0,0,0,0.5);
                    z-index: 99999;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    backdrop-filter: blur(2px);
                `;
                // 点击背景关闭
                overlay.addEventListener('click', function(e) {
                    if (e.target === overlay) {
                        closeModal();
                    }
                });

                // --- 弹窗盒子 ---
                const box = document.createElement('div');
                box.style.cssText = `
                    background: #ffffff;
                    border-radius: 14px;
                    max-width: 90vw;
                    max-height: 80vh;
                    width: 700px;
                    padding: 20px;
                    box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                    overflow-y: auto;
                    position: relative;
                    display: flex;
                    flex-direction: column;
                `;

                // --- 标题栏 ---
                const header = document.createElement('div');
                header.style.cssText = `
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 12px;
                    flex-shrink: 0;
                `;
                const titleEl = document.createElement('h3');
                titleEl.textContent = title;
                titleEl.style.cssText = 'margin: 0; font-size: 1.1rem; color: #1a1d23;';
                const closeBtn = document.createElement('button');
                closeBtn.textContent = '✕';
                closeBtn.style.cssText = `
                    background: transparent;
                    border: none;
                    font-size: 24px;
                    cursor: pointer;
                    color: #949aa5;
                    padding: 0 6px;
                `;
                closeBtn.onmouseover = () => closeBtn.style.color = '#d14343';
                closeBtn.onmouseout = () => closeBtn.style.color = '#949aa5';
                header.appendChild(titleEl);
                header.appendChild(closeBtn);
                box.appendChild(header);

                // --- 内容区 ---
                const contentDiv = document.createElement('div');
                contentDiv.style.cssText = 'flex: 1; overflow-y: auto;';

                // ============================================================
                // 分支1：表格编辑模式（指标数据）
                // ============================================================
                if (editable && field === 'indicator_data' && !forceText) {
                    // 解析 JSON
                    let jsonData = [];
                    try {
                        if (content && content.trim() !== '' && content !== '暂无') {
                            const parsed = JSON.parse(content);
                            if (Array.isArray(parsed)) jsonData = parsed;
                            else jsonData = [parsed];
                        }
                    } catch (e) {
                        jsonData = [{}];
                    }
                    if (jsonData.length === 0) jsonData = [{}];
                    let allKeys = [...new Set(jsonData.flatMap(obj => Object.keys(obj)))];
                    if (allKeys.length === 0) allKeys = ['name', 'value', 'unit', 'reference'];
                    jsonData = jsonData.map(row => {
                        const newRow = {};
                        allKeys.forEach(k => newRow[k] = row[k] !== undefined ? row[k] : '');
                        return newRow;
                    });

                    const editorContext = {
                        data: jsonData,
                        keys: allKeys,
                        recordId: recordId,
                        field: field,
                        container: contentDiv
                    };

                    function getSourceLabel(source) {
                        const map = { 1: '提取', 2: '计算', 3: 'AI' };
                        return map[source] !== undefined ? map[source] : '';
                    }

                    function renderTable() {
                        const container = editorContext.container;
                        if (!container) return;
                        let html = `<style>
                            .json-editor-table { width:100%; border-collapse:collapse; font-size:0.8rem; }
                            .json-editor-table th,.json-editor-table td { border:1px solid #ddd; padding:3px 5px; vertical-align:middle; }
                            .json-editor-table .col-header { width:100%; border:none; background:transparent; font-weight:600; }
                            .json-editor-table .cell-input { width:100%; border:none; background:transparent; padding:3px; outline:none; }
                            .json-editor-table .cell-input:focus { background:#fff; box-shadow:inset 0 0 0 2px #1a6fb5; }
                            .json-editor-table .action-col { width:50px; text-align:center; }
                            .json-editor-table .highlight-row-yellow { background-color:#fff3cd !important; }
                            .json-editor-table .highlight-row-yellow .cell-input { background-color:#fff3cd !important; }
                            .json-editor-table .highlight-row-blue { background-color:#cfe2ff !important; }
                            .json-editor-table .highlight-row-blue .cell-input { background-color:#cfe2ff !important; }
                            .json-actions { margin-top:10px; display:flex; gap:6px; flex-wrap:wrap; align-items:center; }
                            .btn-danger { background:#fee2e2; color:#dc2626; border-color:#fecaca; }
                            .btn-danger:hover { background:#fecaca; }
                        </style>`;
                        html += `<table class="json-editor-table">
                            <caption style="caption-side:top; text-align:left; font-size:0.8rem; color:#6c757d; background:#f1f3f5; padding:2px 8px; border-radius:12px; border:1px solid #dee2e6; margin:0 0 2px 0; line-height:1.3;">
                                💡 黄色：缺失数据； 蓝色：AI默认值
                            </caption>
                            <thead><tr>`;
                        editorContext.keys.forEach((key) => {
                            html += `<th><input class="col-header" value="${escapeHtml(key)}" placeholder="列名" /></th>`;
                        });
                        html += `<th class="action-col">操作</th></tr></thead><tbody>`;
                        editorContext.data.forEach((row, rowIndex) => {
                            const value = row['value'];
                            const source = row.source;
                            let trClass = '';
                            if (source === 3) trClass = 'highlight-row-blue';
                            else if (value === undefined || value === null || value === '') trClass = 'highlight-row-yellow';
                            const trClassAttr = trClass ? `class="${trClass}"` : '';
                            html += `<tr ${trClassAttr}>`;
                            editorContext.keys.forEach((key) => {
                                const val = row[key] !== undefined ? row[key] : '';
                                if (key === 'source') {
                                    const label = getSourceLabel(val);
                                    const displayText = label || '-';
                                    html += `<td><span style="display:inline-block; padding:3px 5px;">${escapeHtml(displayText)}</span></td>`;
                                } else {
                                    html += `<td><input class="cell-input" data-row="${rowIndex}" data-key="${escapeHtml(key)}" value="${escapeHtml(String(val))}" /></td>`;
                                }
                            });
                            html += `<td><button class="btn btn-sm btn-danger" onclick="window._removeRow(${rowIndex})">🗑</button></td>`;
                            html += `</tr>`;
                        });
                        html += `</tbody></table>`;
                        container.innerHTML = html;
                        const btnDiv = document.createElement('div');
                        btnDiv.className = 'json-actions';
                        btnDiv.innerHTML = `
                            <button class="btn btn-outline btn-sm" onclick="window._addRow()">➕ 添加行</button>
                            <button class="btn btn-primary" onclick="window._saveJsonTable()">💾 保存</button>
                            <button class="btn btn-outline" onclick="window._closeModal()">取消</button>
                        `;
                        container.appendChild(btnDiv);
                        window._jsonEditor = editorContext;
                    }

                    window._addRow = function() {
                        const ctx = window._jsonEditor;
                        if (!ctx) return;
                        const newRow = {};
                        ctx.keys.forEach(k => newRow[k] = '');
                        ctx.data.push(newRow);
                        renderTable();
                    };
                    window._removeRow = function(index) {
                        const ctx = window._jsonEditor;
                        if (!ctx) return;
                        if (ctx.data.length <= 1) { showToastPacs('至少保留一行', 'warning'); return; }
                        ctx.data.splice(index, 1);
                        renderTable();
                    };
                    window._saveJsonTable = function() {
                        const ctx = window._jsonEditor;
                        if (!ctx) return;
                        const inputs = ctx.container.querySelectorAll('.cell-input');
                        inputs.forEach(inp => {
                            const rowIdx = parseInt(inp.dataset.row);
                            const key = inp.dataset.key;
                            if (ctx.data[rowIdx]) {
                                ctx.data[rowIdx][key] = inp.value;
                            }
                        });
                        const headers = ctx.container.querySelectorAll('.col-header');
                        const newKeys = [];
                        headers.forEach(inp => {
                            const val = inp.value.trim();
                            if (val) newKeys.push(val);
                        });
                        if (newKeys.length > 0) {
                            const newData = ctx.data.map(row => {
                                const newRow = {};
                                newKeys.forEach(k => { newRow[k] = row[k] !== undefined ? row[k] : ''; });
                                return newRow;
                            });
                            ctx.data = newData;
                            ctx.keys = newKeys;
                        }
                        const jsonString = JSON.stringify(ctx.data);
                        if (typeof saveFieldData === 'function') {
                            saveFieldData(ctx.recordId, ctx.field, jsonString);
                        } else {
                            console.error('saveFieldData 未定义');
                            showToastPacs('保存函数未找到', 'error');
                        }
                    };

                    renderTable();

                    // 关闭函数
                    const closeModalFunc = function() {
                        if (dynamicModal) {
                            document.body.removeChild(dynamicModal);
                            dynamicModal = null;
                        }
                        editingRecordIdModal = null;
                        editingField = null;
                        isEditModeModal = false;
                    };
                    window._closeModal = closeModalFunc;
                    closeBtn.onclick = closeModalFunc;

                    // 组装并显示
                    box.appendChild(contentDiv);
                    overlay.appendChild(box);
                    document.body.appendChild(overlay);
                    dynamicModal = overlay;
                    console.log('[openModal] 表格编辑模式，弹窗已显示');
                    return;
                }

                // ============================================================
                // 分支2：文本编辑模式
                // ============================================================
                if (editable) {
                    const textarea = document.createElement('textarea');
                    textarea.value = content || '';
                    textarea.style.cssText = `
                        width: 100%;
                        min-height: 180px;
                        padding: 10px;
                        border: 1.5px solid #e2e5ea;
                        border-radius: 8px;
                        font-size: 0.9rem;
                        font-family: inherit;
                        line-height: 1.8;
                        resize: vertical;
                        outline: none;
                        box-sizing: border-box;
                    `;
                    textarea.onfocus = function() { this.style.borderColor = '#1a6fb5'; };
                    textarea.onblur = function() { this.style.borderColor = '#e2e5ea'; };
                    contentDiv.appendChild(textarea);

                    const actions = document.createElement('div');
                    actions.style.cssText = 'display: flex; gap: 8px; margin-top: 10px; justify-content: flex-end; flex-shrink: 0;';
                    const cancelBtn = document.createElement('button');
                    cancelBtn.textContent = '取消';
                    cancelBtn.className = 'btn btn-outline';
                    cancelBtn.style.cssText = 'padding: 6px 16px; border-radius: 6px; border: 1.5px solid #e2e5ea; background: #fff; cursor: pointer;';
                    const saveBtn = document.createElement('button');
                    saveBtn.textContent = '💾 保存';
                    saveBtn.className = 'btn btn-primary';
                    saveBtn.style.cssText = 'padding: 6px 16px; border-radius: 6px; border: none; background: #1a6fb5; color: #fff; cursor: pointer;';
                    actions.appendChild(cancelBtn);
                    actions.appendChild(saveBtn);
                    contentDiv.appendChild(actions);

                    const closeModalFunc = function() {
                        if (dynamicModal) {
                            document.body.removeChild(dynamicModal);
                            dynamicModal = null;
                        }
                        editingRecordIdModal = null;
                        editingField = null;
                        isEditModeModal = false;
                    };

                    cancelBtn.onclick = closeModalFunc;
                    closeBtn.onclick = closeModalFunc;

                    saveBtn.onclick = async function() {
                        const newData = textarea.value;
                        if (typeof saveFieldData === 'function') {
                            await saveFieldData(recordId, field, newData);
                        } else {
                            showToastPacs('保存函数未找到', 'error');
                        }
                        closeModalFunc();
                    };

                    box.appendChild(contentDiv);
                    overlay.appendChild(box);
                    document.body.appendChild(overlay);
                    dynamicModal = overlay;
                    console.log('[openModal] 文本编辑模式，弹窗已显示');
                    return;
                }

                // ============================================================
                // 分支3：只读模式（支持分段显示）
                // ============================================================
                // 判断是否为分段对象
                const isSections = typeof content === 'object' && content !== null &&
                                  (content.seen || content.prompt || content.indicator);

                if (isSections) {
                    // --- 分段显示模式 ---
                    const sectionTitles = {
                        seen: '📋 超声所见',
                        prompt: '📋 超声提示',
                        indicator: '📋 检查指标'
                    };
                    // 遍历三个字段，按顺序添加
                    const order = ['indicator', 'seen', 'prompt'];
                    let hasContent = false;
                    for (const key of order) {
                        if (content[key]) {
                            hasContent = true;
                            const sectionDiv = document.createElement('div');
                            sectionDiv.style.cssText = 'margin-bottom: 16px; border-bottom: 1px solid #e2e5ea; padding-bottom: 12px;';

                            // 标题栏（含复制按钮）
                            const headerDiv = document.createElement('div');
                            headerDiv.style.cssText = 'display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;';
                            const titleSpan = document.createElement('span');
                            titleSpan.textContent = sectionTitles[key] || key;
                            titleSpan.style.cssText = 'font-weight:600; font-size:0.9rem;';
                            headerDiv.appendChild(titleSpan);

                            const copyBtn = document.createElement('button');
                            copyBtn.textContent = '📋 复制';
                            copyBtn.style.cssText = 'padding: 2px 10px; border:1px solid #ccc; border-radius:4px; background:#fff; cursor:pointer; font-size:0.7rem;';
                            // 闭包保存当前文本
                            const text = content[key];
                            copyBtn.onclick = function() {
                                if (navigator.clipboard && navigator.clipboard.writeText) {
                                    navigator.clipboard.writeText(text)
                                        .then(() => showToast('✅ 已复制', 'success'))
                                        .catch(() => fallbackCopy(text));
                                } else {
                                    fallbackCopy(text);
                                }
                            };
                            headerDiv.appendChild(copyBtn);
                            sectionDiv.appendChild(headerDiv);

                            // 内容
                            const contentPre = document.createElement('div');
                            contentPre.style.cssText = 'white-space: pre-wrap; font-size:0.9rem; line-height:1.8;';
                            contentPre.textContent = text;
                            sectionDiv.appendChild(contentPre);
                            contentDiv.appendChild(sectionDiv);
                        }
                    }
                    if (!hasContent) {
                        // 如果没有内容，显示占位
                        const empty = document.createElement('div');
                        empty.textContent = '暂无报告内容';
                        empty.style.cssText = 'color: var(--text-muted);';
                        contentDiv.appendChild(empty);
                    }

                    // 关闭按钮事件
                    const closeModalFunc = function() {
                        if (dynamicModal) {
                            document.body.removeChild(dynamicModal);
                            dynamicModal = null;
                        }
                        editingRecordIdModal = null;
                        editingField = null;
                        isEditModeModal = false;
                    };
                    closeBtn.onclick = closeModalFunc;  // <--- 添加这一行
                    // 组装弹窗
                    box.appendChild(contentDiv);
                    overlay.appendChild(box);
                    document.body.appendChild(overlay);
                    dynamicModal = overlay;
                    console.log('[openModal] 分段只读模式，弹窗已显示');
                    return;
                }

                // ---- 原有的纯文本只读模式（兼容旧调用） ----
                // 安全处理 content（字符串或对象转字符串）
                let displayContent = '暂无内容';
                if (content !== undefined && content !== null && content !== '') {
                    if (typeof content === 'string') {
                        displayContent = content;
                    } else if (typeof content === 'object') {
                        try {
                            displayContent = JSON.stringify(content, null, 2);
                        } catch (e) {
                            displayContent = String(content);
                        }
                    } else {
                        displayContent = String(content);
                    }
                }
                console.log('[openModal] displayContent length:', displayContent.length);

                // ---- 在标题栏添加复制按钮 ----
                const copyBtn = document.createElement('button');
                copyBtn.textContent = '📋 复制';
                copyBtn.style.cssText = `
                    padding: 4px 12px;
                    border: 1px solid #e2e5ea;
                    border-radius: 6px;
                    background: #fff;
                    cursor: pointer;
                    font-size: 0.8rem;
                    margin-right: 12px;
                `;
                copyBtn.onclick = function() {
                    const textToCopy = displayContent;
                    if (navigator.clipboard && navigator.clipboard.writeText) {
                        navigator.clipboard.writeText(textToCopy)
                            .then(() => showToast('已复制', 'success'))
                            .catch(() => fallbackCopy(textToCopy));
                    } else {
                        fallbackCopy(textToCopy);
                    }
                };
                // 重新组织标题栏
                const oldClose = closeBtn;
                header.innerHTML = '';
                header.appendChild(titleEl);
                header.appendChild(copyBtn);
                header.appendChild(oldClose);

                // 内容区显示纯文本
                const pre = document.createElement('div');
                pre.style.cssText = 'white-space: pre-wrap; font-size: 0.9rem; line-height: 1.8;';
                pre.textContent = displayContent;
                contentDiv.appendChild(pre);

                // 关闭按钮事件
                const closeModalFunc = function() {
                    if (dynamicModal) {
                        document.body.removeChild(dynamicModal);
                        dynamicModal = null;
                    }
                    editingRecordIdModal = null;
                    editingField = null;
                    isEditModeModal = false;
                };
                oldClose.onclick = closeModalFunc;

                // 组装
                box.appendChild(contentDiv);
                overlay.appendChild(box);
                document.body.appendChild(overlay);
                dynamicModal = overlay;
                console.log('[openModal] 纯文本只读模式，弹窗已显示，内容预览:', pre.textContent.substring(0, 50));

            } catch (e) {
                console.error('[openModal] 错误:', e);
                showToastPacs('打开弹窗失败：' + e.message, 'error');
            }
        }

        // ===== closeModal 函数（兼容旧代码调用） =====
        function closeModal() {
            if (dynamicModal) {
                document.body.removeChild(dynamicModal);
                dynamicModal = null;
            }
            editingRecordIdModal = null;
            editingField = null;
            isEditModeModal = false;
            // 隐藏原有的 modalOverlay（以防万一）
            if (typeof modalOverlay !== 'undefined' && modalOverlay) {
                modalOverlay.style.display = 'none';
            }
            console.log('[closeModal] 弹窗已关闭');
        }


        modalCloseBtn.addEventListener('click', closeModal);
        modalOverlay.addEventListener('click', (e) => { if (e.target === modalOverlay) closeModal(); });

        async function saveFieldData(recordId, field, newData) {
            if (!recordId) { showToastPacs('记录ID无效', 'error'); return; }
            if (!newData || newData.trim().length === 0) { showToastPacs('内容不能为空', 'warning'); return; }
            showLoading(true);
            try {
                const updateData = {};
                updateData[field] = newData;
                const resp = await fetch(`${API_BASE}/asr/pacs_ai_report/${recordId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(updateData)
                });
                if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
                const result = await resp.json();
                if (result.success === false) { throw new Error(result.message || '保存失败'); }
                const fieldLabel = field === 'patient_info' ? '患者信息' : '指标数据';
                showToastPacs(`${fieldLabel}已更新 ✅`, 'success');
                closeModal();
                loadReports(currentPage);
            } catch (err) {
                showToastPacs('保存失败：' + err.message, 'error');
            } finally { showLoading(false); }
        }

        // ---- 患者查询 ----
        async function queryPatient() {
            if (isEditMode) {
                showToastPacs('当前处于编辑模式，请先取消编辑或完成重新提交', 'warning');
                return;
            }
            const zhuyuanhao = zhuyuanhaoInput.value.trim();
            if (!zhuyuanhao) { showToastPacs('请输入住院号/门诊号', 'warning'); return; }
            const patientTypeSelect = document.getElementById('patientTypeSelect');
            const patientType = patientTypeSelect ? patientTypeSelect.value : 'inpatient';
            const checkTypeSelect = document.getElementById('checkTypeSelect');
            const checkType = checkTypeSelect ? checkTypeSelect.value : 'US';
            showLoading(true);
            try {
                const resp = await fetch(`${API_BASE}/asr/patient_pacs_info/${zhuyuanhao}/${patientType}/${checkType}`);
                if (!resp.ok) throw new Error('患者信息查询失败');
                const data = await resp.json();
                currentPatient = data;
                displayPatientInfo(data);
                const items = data.check_items_list || [];
                if (items.length === 1) {
                    selectedCheckItem = items[0].check_item;
                    selectedYizhuid = items[0].yizhuid;
                    highlightCheckItem(selectedCheckItem);
                } else {
                    selectedCheckItem = null;
                    selectedYizhuid = null;
                }
                updateSubmitButton();
            } catch (err) {
                showToastPacs('查询失败：' + err.message, 'error');
                patientInfoArea.style.display = 'none';
                currentPatient = null;
                updateSubmitButton();
            } finally { showLoading(false); }
        }

        function displayPatientInfo(data) {
            pName.textContent = data.patient_name || '-';
            pSex.textContent = data.patient_sex || '-';
            pAge.textContent = data.patient_age || '-';
            pDept.textContent = data.dept_name || '-';
            patientInfoArea.style.display = 'block';

            const items = data.check_items_list || [];
            checkItemsContainer.innerHTML = '';
            if (items.length === 0) {
                checkItemsContainer.innerHTML = '<span style="color:var(--text-muted);">无检查项目</span>';
                return;
            }

            items.forEach(item => {
                const wrapper = document.createElement('div');
                wrapper.className = 'check-item-wrapper';
                const isDone = item.status === 1;
                const reportId = item.report_id; // 可能为 null/undefined/0
                const isManual = isDone && (reportId === 0 || reportId === null || reportId === undefined);
                const isAI = isDone && !isManual;

                if (isDone) wrapper.classList.add('done');

                // 状态徽章
                let statusBadge;
                if (isDone) {
                    if (isManual) {
                        // 人工报告：橙色
                        statusBadge = `<span style="background:#fef3c7;color:#c0792b;padding:2px 8px;border-radius:12px;font-size:0.65rem;">已做 (人工报告)</span>`;
                    } else {
                        // AI 报告：绿色
                        statusBadge = `<span style="background:#e6f4ec;color:#2d8a56;padding:2px 8px;border-radius:12px;font-size:0.65rem;">✅ 已做 (AI报告)</span>`;
                    }
                } else {
                    // 未做：橙色
                    statusBadge = '<span style="background:#fef3c7;color:#c0792b;padding:2px 8px;border-radius:12px;font-size:0.65rem;">⏳ 未做</span>';
                }

                // 重新编辑按钮（仅已做时显示）
                let reeditHtml = '';
                if (isAI) {
                    const btnLabel = '✏️ 重新编辑';
                    reeditHtml = `<div style="margin-top:4px;"><button class="btn btn-sm btn-reedit" style="font-size:0.65rem; padding:2px 8px;">${btnLabel}</button></div>`;
                }

                wrapper.innerHTML = `
                    <div class="item-name" style="display:flex; justify-content:space-between; align-items:center;">
                        <span>${escapeHtml(item.check_item)}  -  ${escapeHtml(item.kaishisj)}</span>
                        ${statusBadge}
                    </div>
                    <div class="item-meta">
                        <span>医嘱ID: ${escapeHtml(item.yizhuid)}</span>
                        <span>开嘱: ${escapeHtml(item.kaizhusj)}</span>
                        <span>开始: ${escapeHtml(item.kaishisj)}</span>
                        <span>类型: ${escapeHtml(item.jianchabzfl)}</span>
                    </div>
                    ${reeditHtml}
                `;

                // 存储数据到 dataset
                wrapper.dataset.value = item.check_item;
                wrapper.dataset.yizhuid = item.yizhuid;
                wrapper.dataset.status = item.status;
                wrapper.dataset.reportId = reportId;
                wrapper.dataset.isManual = isManual;
                wrapper.dataset.patientInfo = item.patient_info || null;

                // ----- 点击事件（修改此处） -----
                wrapper.addEventListener('click', function(e) {
                    if (e.target.closest('button')) return; // 按钮事件单独处理

                    if (this.dataset.status == 1) {
                        // 已做：判断是否为 AI 报告（reportId > 0）
                        const reportIdVal = parseInt(this.dataset.reportId);
                        if (reportIdVal > 0) {
                            // AI 报告：加载报告进入编辑
                            loadReportForEdit(
                                this.dataset.reportId,
                                this.dataset.patientInfo,
                                this.dataset.yizhuid,
                                this.dataset.value,
                                this.dataset.isManual === 'true'
                            );
                            return;
                        } else {
                            // 人工报告（reportId == 0 或 null）：行为同未做，只选中，启用提交
                            // 不进入编辑，只选中
                        }
                    }

                    // 未做 或 人工报告：选中，启用提交
                    document.querySelectorAll('.check-item-wrapper').forEach(el => el.classList.remove('selected'));
                    this.classList.add('selected');
                    selectedCheckItem = this.dataset.value;
                    selectedYizhuid = this.dataset.yizhuid;
                    updateSubmitButton();
                });

                // 重新编辑按钮事件（保持不变，点击后进入编辑模式）
                const reeditBtn = wrapper.querySelector('.btn-reedit');
                if (reeditBtn) {
                    reeditBtn.addEventListener('click', function(e) {
                        e.stopPropagation();
                        const parent = this.closest('.check-item-wrapper');
                        loadReportForEdit(
                            parent.dataset.reportId,
                            parent.dataset.patientInfo,
                            parent.dataset.yizhuid,
                            parent.dataset.value,
                            parent.dataset.isManual === 'true'
                        );
                    });
                }

                checkItemsContainer.appendChild(wrapper);
            });

            // 若只有一个未做项，默认选中（保留原逻辑）
            if (items.length === 1 && items[0].status === 0) {
                const first = checkItemsContainer.querySelector('.check-item-wrapper');
                if (first) {
                    first.classList.add('selected');
                    selectedCheckItem = first.dataset.value;
                    selectedYizhuid = first.dataset.yizhuid;
                    updateSubmitButton();
                }
            }
        }

        async function loadReportForEdit(reportId, patientInfo, yizhuid, checkItem) {
            // 从 currentPatient 获取患者基本信息
            if (!currentPatient) {
                showToastPacs('患者信息缺失', 'error');
                return;
            }

            // 构造 record 对象
            let record = {
                id: reportId,
                patient_name: currentPatient.patient_name || '-',
                patient_sex: currentPatient.patient_sex || '-',
                patient_age: currentPatient.patient_age || '-',
                dept_name: currentPatient.dept_name || '-',
                zhuyuanhao: currentPatient.zhuyuanhao || '',
                check_items: checkItem,
                yizhuid: yizhuid,
                submit_time: new Date().toLocaleString(), // 或从后端获取
                patient_info: patientInfo || ''  // 如果已有内容则直接使用
            };

            // 如果 patientInfo 为空，则通过 reportId 获取
            if (!record.patient_info && reportId) {
                showLoading(true);
                try {
                    const resp = await fetch(`${API_BASE}/asr/pacs_ai_report/${reportId}`);
                    if (!resp.ok) throw new Error('获取报告失败');
                    const data = await resp.json();
                    // 提取报告内容，与 viewReport 中类似
                    let content = data.patient_info || data.report?.patient_info || '';
                    if (!content) {
                        content = data.report?.ai_report || data.report?.report || data.report?.content || '';
                    }
                    record.patient_info = content;
                } catch (err) {
                    showToastPacs('加载报告失败：' + err.message, 'error');
                    showLoading(false);
                    return;
                } finally {
                    showLoading(false);
                }
            }

            // 调用 startEdit（它会处理确认对话框和编辑模式设置）
            startEdit(record);
        }

        function highlightCheckItem(item) {
            document.querySelectorAll('.check-item-wrapper').forEach(el => {
                el.classList.toggle('selected', el.dataset.value === item);
            });
        }

        function updateSubmitButton() {
            const hasPatient = currentPatient !== null;
            const hasItem = selectedCheckItem !== null;
            const hasFindings = document.getElementById('examFindings').value.trim().length > 0;
            submitBtn.disabled = !(hasPatient && hasItem && hasFindings);
        }

        function clearEditArea() {
            examFindingsTextarea.value = '';
            fullText = '';
            currentStash = '';
            sentenceCountVal = 0;
            sentenceCountEl.textContent = '0';
            updateWordCount();
            clearDraft();
        }

        function hasPendingContent() {
            return examFindingsTextarea.value.trim().length > 0;
        }

        // ---- 重新编辑 ----
        async function startEdit(record) {
            if (hasPendingContent()) {
                const confirmed = await showConfirmDialog(
                    '清空当前内容',
                    `当前有未提交的内容，确认清空并加载患者【${record.patient_name || '未知患者'}】的记录继续重新编辑吗？`
                );
                if (!confirmed) return;
                clearEditArea();
            }
            beforeEditFullText = fullText;
            beforeEditExamFindings = examFindingsTextarea.value;

            isEditMode = true;
            editingRecordId = record.id;
            editingRecordData = record;

            // 重新绑定取消编辑按钮（确保在 PyQt5 中有效）
            cancelEditBtn.onclick = cancelEdit;  // 直接赋值覆盖之前绑定

            const patientData = {
                patient_name: record.patient_name || '-',
                patient_sex: record.patient_sex || '-',
                patient_age: record.patient_age || '-',
                dept_name: record.dept_name || '-',
                zhuyuanhao: record.zhuyuanhao || '',
                check_items_list: [{
                    check_item: record.check_items || '-',
                    yizhuid: record.yizhuid || '',
                    kaishisj: record.submit_time || '',
                    kaizhusj: '',
                    jianchabzfl: ''
                }]
            };
            currentPatient = patientData;
            displayPatientInfo(patientData);
            if (patientData.check_items_list.length === 1) {
                selectedCheckItem = patientData.check_items_list[0].check_item;
                selectedYizhuid = patientData.check_items_list[0].yizhuid;
                highlightCheckItem(selectedCheckItem);
            }
            const patientInfo = record.patient_info || '';
            examFindingsTextarea.value = patientInfo;
            fullText = patientInfo;
            currentStash = '';
            sentenceCountVal = patientInfo.split(/[。！？\n]/).filter(s => s.trim().length > 0).length;
            sentenceCountEl.textContent = sentenceCountVal;
            updateWordCount();
            saveDraft();
            zhuyuanhaoInput.value = record.zhuyuanhao || '';
            submitBtn.textContent = '🔄 重新提交';
            submitBtn.disabled = false;
            editModeBadge.classList.add('show');
            queryBtn.textContent = '🔍 查询';
            showToastPacs(`已加载记录 #${record.id} 进入编辑模式`, 'info');
        }

        async function cancelEdit() {
            console.log('cancelEdit called, isEditMode:', isEditMode);
            if (!isEditMode) {
                console.log('Not in edit mode, return');
                return;
            }
            if (hasPendingContent()) {
                const confirmed = await showConfirmDialog('取消编辑', '确定要取消编辑吗？当前修改将丢失。');
                if (!confirmed) return;
            }
            clearEditArea();
            patientInfoArea.style.display = 'none';
            currentPatient = null;
            selectedCheckItem = null;
            selectedYizhuid = null;
            zhuyuanhaoInput.value = '';
            exitEditMode();
            showToastPacs('已取消编辑', 'info');
        }

        function exitEditMode() {
            isEditMode = false;
            editingRecordId = null;
            editingRecordData = null;
            submitBtn.textContent = '⚡ 提交';
            submitBtn.disabled = true;
            editModeBadge.classList.remove('show');
            queryBtn.textContent = '🔍 查询';
            loadReports(currentPage);
        }

        function resetPatientInfo() {
            // 隐藏患者信息区域
            patientInfoArea.style.display = 'none';
            // 清空状态变量
            currentPatient = null;
            selectedCheckItem = null;
            selectedYizhuid = null;
            // 清除所有检查项的选中状态
            document.querySelectorAll('.check-item-wrapper').forEach(el => el.classList.remove('selected'));
            // 更新提交按钮状态（禁用）
            updateSubmitButton();
            // 清空住院号输入框（可选，如果希望一并清空）
            // zhuyuanhaoInput.value = '';
        }

        // ---- 提交报告 ----
        async function submitReport() {
            if (submitBtn.disabled) return;
            if (window.isRecording && window.isRecording()) {
                await window.stopRecording();
            }
            const examFindings = document.getElementById('examFindings').value.trim();
            if (!examFindings) {
                showToastPacs('检查所见不能为空', 'warning');
                return;
            }
            const patientTypeSelect = document.getElementById('patientTypeSelect');
            const patientType = patientTypeSelect ? patientTypeSelect.value : 'inpatient';

            if (isEditMode && editingRecordId) {
                showLoading(true);
                submitBtn.disabled = true;
                try {
                    const updateData = {
                        patient_info: examFindings,
                        re_edit: true
                    };
                    const resp = await fetch(`${API_BASE}/asr/pacs_ai_report/${editingRecordId}`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(updateData)
                    });
                    if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
                    const result = await resp.json();
                    if (result.success === false) {
                        throw new Error(result.message || '更新失败');
                    }
                    showToastPacs('报告已更新，正在重新生成...', 'success');
                    clearEditArea();
                    exitEditMode();
                    loadReports(currentPage);
                } catch (err) {
                    showToastPacs('重新提交失败：' + err.message, 'error');
                } finally {
                    showLoading(false);
                    submitBtn.disabled = false;
                    resetPatientInfo();
                }
                return;
            }

            if (!currentPatient) {
                showToastPacs('请先查询患者信息', 'warning');
                return;
            }
            if (!selectedCheckItem) {
                showToastPacs('请选择一个检查项目', 'warning');
                return;
            }
            const data = {
                zhuyuanhao: currentPatient.zhuyuanhao,
                patient_name: currentPatient.patient_name,
                patient_age: String(currentPatient.patient_age),
                patient_sex: currentPatient.patient_sex,
                dept_id: String(currentPatient.dept_id),
                dept_name: currentPatient.dept_name,
                yizhiid: currentPatient.yizhiid,
                check_items: selectedCheckItem,
                yizhuid: selectedYizhuid,
                patient_info: examFindings,
                patient_type: patientType
            };
            showLoading(true);
            submitBtn.disabled = true;
            try {
                const resp = await fetch(`${API_BASE}/asr/pacs-submit`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                if (!resp.ok) throw new Error(`提交失败 ${resp.status}: ${resp.statusText}`);
                const result = await resp.json();
                if (result.success === false) {
                    throw new Error(result.message || '提交失败，请检查数据');
                }
                showToastPacs('提交成功，报告生成中...', 'success');
                document.getElementById('examFindings').value = '';
                fullText = '';
                currentStash = '';
                sentenceCountVal = 0;
                sentenceCountEl.textContent = '0';
                updateWordCount();
                clearDraft();
                loadReports(currentPage);
                updateSubmitButton();
            } catch (err) {
                showToastPacs('提交失败：' + err.message, 'error');
            } finally {
                showLoading(false);
                submitBtn.disabled = false;

                resetPatientInfo();
            }
        }

        // ---- 历史报告加载 ----
        async function loadReports(page = 1) {
            showLoading(true);
            try {
                const url = `${API_BASE}/asr/pacs_ai_reports?page=${page}&page_size=${PAGE_SIZE}`;
                const resp = await fetch(url);
                if (!resp.ok) throw new Error('获取列表失败');
                const result = await resp.json();
                const data = result.data || [];
                const total = result.total || 0;
                renderTable(data);
                renderPagination(page, total);
            } catch (err) {
                showToastPacs('加载列表失败：' + err.message, 'error');
            } finally { showLoading(false); }
        }

        function renderTable(data) {
            if (!data || data.length === 0) {
                reportTableBody.innerHTML = `<tr><td colspan="12" style="text-align:center;color:var(--text-muted);">暂无记录</td></tr>`;
                return;
            }
            window._reportTableData = data;
            let html = '';
            data.forEach((item, index) => {
                const statusText = item.report_status === 1 ?
                    '报告已生成' :
                    (item.indicator_status === 1 ?
                        '报告生成中' :
                        (item.indicator_status === 0 && item.indicator_data === null ?
                            '指标提取中' :
                            '指标不完善，请补充'));
                const statusClass = item.report_status === 1 ? 'generated' : (item.indicator_status === 1 ? 'processing' : 'pending');
                const btnDisabled = item.report_status !== 1;
                // <td>${item.patient_sex || '-'}</td>
                // <td>${item.patient_age || '-'}</td>
                html += `<tr data-record-id="${item.id}" data-index="${index}">
                        <td>${item.zhuyuanhao || '-'}</td>
                        <td>${item.patient_type || '-'}</td>
                        <td>${item.patient_name || '-'} ${item.patient_sex || '-'} ${item.patient_age || '-'}</td>

                        <td>${item.check_items || '-'}</td>
                        <td>${item.submit_time || '-'}</td>
                        <td><span class="status-badge ${statusClass}">${statusText}</span></td>
                        <td><button class="btn-detail edit-field" data-index="${index}" data-field="patient_info">✏️ 查看</button></td>
                        <td><button class="btn-detail edit-field" data-index="${index}" data-field="indicator_data">✏️ 查看</button></td>
                        <td><button class="btn-detail edit-field-text" data-index="${index}" data-field="indicator_data">📝 文本</button></td>
                        <td>
                            <button class="btn-view" data-id="${item.id}" ${btnDisabled ? 'disabled' : ''}>
                                ${btnDisabled ? '⏳ 生成中' : '📄 查看'}
                            </button>
                            <button class="btn-reedit" data-id="${item.id}" data-index="${index}" title="重新编辑此报告">✏️ 重新编辑</button>
                        </td>
                    </tr>`;
            });
            reportTableBody.innerHTML = html;

            reportTableBody.querySelectorAll('.edit-field').forEach(btn => {
                btn.addEventListener('click', function(e) {
                    e.stopPropagation();
                    const index = parseInt(this.dataset.index);
                    const field = this.dataset.field;
                    const record = window._reportTableData[index];
                    if (!record) { showToastPacs('数据不存在', 'error'); return; }
                    const content = record[field] || '暂无';
                    const label = field === 'patient_info' ? '患者信息' : '指标数据';
                    openModal(`📋 ${label}（可编辑）`, content, true, record.id, field);
                });
            });
            reportTableBody.querySelectorAll('.edit-field-text').forEach(btn => {
                btn.addEventListener('click', function(e) {
                    e.stopPropagation();
                    const index = parseInt(this.dataset.index);
                    const record = window._reportTableData[index];
                    if (!record) { showToastPacs('数据不存在', 'error'); return; }
                    const content = record.indicator_data || '暂无';
                    openModal('📋 指标数据（文本编辑）', content, true, record.id, 'indicator_data', true);
                });
            });
            reportTableBody.querySelectorAll('.btn-view:not([disabled])').forEach(btn => {
                btn.addEventListener('click', function(e) {
                    e.stopPropagation();
                    const id = this.dataset.id;
                    viewReport(id);
                });
            });
            reportTableBody.querySelectorAll('.btn-reedit').forEach(btn => {
                btn.addEventListener('click', function(e) {
                    e.stopPropagation();
                    const index = parseInt(this.dataset.index);
                    const record = window._reportTableData[index];
                    if (!record) { showToastPacs('数据不存在', 'error'); return; }
                    startEdit(record);
                });
            });
            reportTableBody.querySelectorAll('tr[data-record-id]').forEach(row => {
                row.addEventListener('dblclick', async function(e) {
                    e.preventDefault();  // <--- 添加这一行
                    if (e.target.closest('button')) return;
                    const recordId = this.dataset.recordId;
                    const index = parseInt(this.dataset.index);
                    const record = window._reportTableData[index];
                    if (!record) return;
                    const confirmed = await showConfirmDialog(
                        '重新编辑记录',
                        `确认重新编辑 #${recordId} 患者【${record.patient_name || '未知患者'}】的记录吗？\n当前页面未提交的内容将被清空。`
                    );
                    if (confirmed) {
                        startEdit(record);
                    }
                });
                row.addEventListener('mouseenter', function() { this.classList.add('reedit-hover'); });
                row.addEventListener('mouseleave', function() { this.classList.remove('reedit-hover'); });
            });
        }

        function renderPagination(current, total) {
            const totalPages = Math.ceil(total / PAGE_SIZE);
            if (totalPages <= 1) { paginationControls.innerHTML = ''; return; }
            let html = '';
            html += `<button ${current <= 1 ? 'disabled' : ''} data-page="${current-1}">◀</button>`;
            for (let i = 1; i <= totalPages; i++) {
                html += `<button class="${i === current ? 'active' : ''}" data-page="${i}">${i}</button>`;
            }
            html += `<button ${current >= totalPages ? 'disabled' : ''} data-page="${current+1}">▶</button>`;
            paginationControls.innerHTML = html;
            paginationControls.querySelectorAll('button[data-page]').forEach(btn => {
                btn.addEventListener('click', function() {
                    const page = parseInt(this.dataset.page);
                    if (!isNaN(page) && page >= 1 && page <= totalPages) {
                        currentPage = page;
                        loadReports(page);
                    }
                });
            });
        }

        async function viewReport(reportId) {
            showLoading(true);
            try {
                const resp = await fetch(`${API_BASE}/asr/pacs_ai_report/${reportId}`);
                if (!resp.ok) throw new Error('获取报告失败');
                const data = await resp.json();

                // 构造分段数据
                let sections = {};
                if (data.report) {
                    // 超声所见
                    if (data.report.seen) {
                        sections.seen = data.report.seen;
                    }
                    // 超声提示
                    if (data.report.prompt) {
                        sections.prompt = data.report.prompt;
                    }
                    // 检查指标（可能为对象或字符串）
                    if (data.report.indicator_data) {
                        let indicatorText = data.report.indicator_data;
                        if (typeof indicatorText === 'object') {
                            indicatorText = JSON.stringify(indicatorText, null, 2);
                        }
                        sections.indicator = indicatorText;
                    }
                    // 如果没有分段的字段，则尝试取旧版 ai_report 或报告内容
                    if (Object.keys(sections).length === 0) {
                        if (data.report.ai_report) {
                            sections.seen = data.report.ai_report;
                        } else if (data.report.report) {
                            sections.seen = data.report.report;
                        } else if (data.report.content) {
                            sections.seen = data.report.content;
                        } else {
                            sections.seen = JSON.stringify(data.report, null, 2);
                        }
                    }
                } else if (data.ai_report) {
                    sections.seen = data.ai_report;
                } else if (data.content) {
                    sections.seen = data.content;
                } else {
                    sections.seen = JSON.stringify(data, null, 2);
                }
                openModal('📄 报告详情', sections, false);
            } catch (err) {
                showToastPacs('查看报告失败：' + err.message, 'error');
            } finally { showLoading(false); }
        }

        // ---- 历史折叠 + 互斥逻辑 ----
        const historyToggle = document.getElementById('historyToggle');
        const historyContent = document.getElementById('historyContent');
        const toggleIcon = document.getElementById('toggleIcon');
        // 默认折叠
        let historyOpen = localStorage.getItem('historyOpen') === 'true';
        if (historyOpen) {
            historyContent.style.display = 'block';
            toggleIcon.textContent = '▼';
            // 历史展开，隐藏报告面板
            // reportPanel.classList.add('hidden');
        } else {
            historyContent.style.display = 'none';
            toggleIcon.textContent = '▶';
            // reportPanel.classList.remove('hidden');
        }

        historyToggle.addEventListener('click', function() {
            const isOpen = historyContent.style.display !== 'none';
            if (isOpen) {
                // 折叠历史
                historyContent.style.display = 'none';
                toggleIcon.textContent = '▶';
                localStorage.setItem('historyOpen', 'false');
                // reportPanel.classList.remove('hidden');  // 显示报告面板
            } else {
                // 展开历史
                historyContent.style.display = 'block';
                toggleIcon.textContent = '▼';
                localStorage.setItem('historyOpen', 'true');
                // reportPanel.classList.add('hidden');    // 隐藏报告面板
            }
        });

        // ---- 事件绑定 ----submitReport
        queryBtn.addEventListener('click', queryPatient);
        zhuyuanhaoInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') queryPatient(); });
        submitBtn.addEventListener('click', submitReport);
        refreshListBtn.addEventListener('click', () => loadReports(currentPage));
        document.getElementById('examFindings').addEventListener('input', updateSubmitButton);
        cancelEditBtn.addEventListener('click', cancelEdit);

        // ---- 初始化 ----
        loadReports(1);
        submitBtn.disabled = true;
        console.log('报告模块初始化完成');
    })();
})();