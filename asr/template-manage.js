/* template-manage.js - 模板与词条管理模块（独立，不影响主功能） */
(function() {
    'use strict';

    /* ========== API 配置（与 asr.js 保持一致） ========== */
    function getApiConfig() {
        const host = window.location.hostname;
        const portMap = {
            'oa.nsyy.com.cn': 6080,
            '192.168.3.12':   6083,
            '192.168.124.9':  8081,
            '127.0.0.1':      8081,
            'localhost':      8081,
        };
        const port = portMap[host] || 8081;
        if (host === 'oa.nsyy.com.cn') return `https://${host}:6081/mz`;
        if (host === '192.168.3.12')   return `https://${host}:6083/mz`;
        return `http://${host}:${port}/mz`;
    }
    const API_BASE = getApiConfig();
    const PAGE_SIZE = 15;

    /* ========== 工具函数 ========== */
    const $  = (s, ctx) => (ctx || document).querySelector(s);
    const $$ = (s, ctx) => Array.from((ctx || document).querySelectorAll(s));

    function escapeHtml(t) {
        const d = document.createElement('div');
        d.textContent = t == null ? '' : String(t);
        return d.innerHTML;
    }

    /* ========== 预览单元格渲染（支持展开/折叠） ========== */
    function renderPreviewCell(text, collapseThreshold) {
        if (text === null || text === undefined || text === '') {
            return '<span class="tm-cell-empty">—</span>';
        }
        var s = String(text);
        var lines = s.split('\n').length;
        var threshold = collapseThreshold || 60;
        var isLong = s.length > threshold || lines > 3;

        var escaped = escapeHtml(s);
        if (!isLong) {
            return '<div class="tm-cell-wrap"><div class="tm-cell-text">' + escaped + '</div></div>';
        }
        return '<div class="tm-cell-wrap">' +
            '<div class="tm-cell-text tm-cell-collapsed">' + escaped + '</div>' +
            '<button type="button" class="tm-cell-toggle" data-more="0">' +
                '展开 ▾ <span class="tm-cell-meta">共 ' + s.length + ' 字</span>' +
            '</button>' +
        '</div>';
    }

    /* ========== 绑定展开/折叠事件 ========== */
    function bindCellToggles(container) {
        $$('.tm-cell-toggle', container).forEach(function(btn) {
            btn.onclick = function(e) {
                e.stopPropagation();
                var wrap = btn.parentNode;
                var cell = wrap.querySelector('.tm-cell-text');
                if (!cell) return;
                var isExpanded = btn.dataset.more === '1';
                var total = cell.textContent.length;

                if (isExpanded) {
                    cell.classList.remove('tm-cell-expanded');
                    cell.classList.add('tm-cell-collapsed');
                    btn.dataset.more = '0';
                    btn.innerHTML = '展开 ▾ <span class="tm-cell-meta">共 ' + total + ' 字</span>';
                } else {
                    cell.classList.remove('tm-cell-collapsed');
                    cell.classList.add('tm-cell-expanded');
                    btn.dataset.more = '1';
                    btn.innerHTML = '收起 ▴';
                }
            };
        });
    }

    function toast(msg, type = 'info') {
        const container = document.getElementById('toastContainer');
        if (!container) return;
        const el = document.createElement('div');
        el.className = 'toast ' + type;
        const icons = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' };
        el.textContent = (icons[type] || '') + ' ' + msg;
        container.appendChild(el);
        setTimeout(() => {
            if (el.parentNode) {
                el.classList.add('removing');
                el.addEventListener('animationend', () => el.remove());
            }
        }, 3000);
    }

    function confirmDialog(title, message) {
        return new Promise(resolve => {
            const overlay = document.createElement('div');
            overlay.className = 'tm-form-overlay';
            overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:999999;display:flex;align-items:center;justify-content:center;backdrop-filter:blur(2px);';
            const box = document.createElement('div');
            box.style.cssText = 'background:#fff;border-radius:14px;max-width:440px;width:90%;padding:24px 20px 20px;box-shadow:0 20px 60px rgba(0,0,0,0.3);text-align:center;';
            box.innerHTML = `
                <div style="font-size:2.2rem;margin-bottom:10px;">⚠️</div>
                <h3 style="font-size:1rem;margin-bottom:6px;color:#1a1d23;font-weight:700;">${escapeHtml(title)}</h3>
                <p style="font-size:0.9rem;color:#5f6570;margin-bottom:16px;white-space:pre-wrap;">${escapeHtml(message)}</p>
                <div style="display:flex;justify-content:center;gap:10px;">
                    <button class="tm-cancel-btn" style="padding:6px 16px;border-radius:6px;border:1.5px solid #e2e5ea;background:#fff;cursor:pointer;min-width:70px;font-family:inherit;">取消</button>
                    <button class="tm-ok-btn" style="padding:6px 16px;border-radius:6px;border:none;background:#1a6fb5;color:#fff;cursor:pointer;min-width:70px;font-family:inherit;font-weight:600;">确定</button>
                </div>
            `;
            overlay.appendChild(box);
            document.body.appendChild(overlay);
            const close = (val) => { overlay.remove(); resolve(val); };
            $('.tm-cancel-btn', box).onclick = () => close(false);
            $('.tm-ok-btn', box).onclick = () => close(true);
            setTimeout(() => $('.tm-ok-btn', box).focus(), 100);
        });
    }

    /* ========== 状态 ========== */
    const state = {
    activeTab: 'template',
    template: { page: 1, total: 0, keyword: '', list: [] },
    entry:    { page: 1, total: 0, keyword: '', list: [] },
    checkItems: [],
    checkItemOptions: null,   // ★ 新增：缓存检查项目下拉选项
};

    /* ========== 视图切换 ========== */
    const mainWrapper   = document.querySelector('.main-wrapper');
    const templateView  = document.getElementById('templateManageView');

    function showTemplateView() {
        if (mainWrapper)  mainWrapper.style.display = 'none';
        if (templateView) templateView.style.display = 'block';
        if (state.activeTab === 'template') loadTemplates(1);
        else loadEntries(1);
    }
    function showMainView() {
        if (templateView) templateView.style.display = 'none';
        if (mainWrapper)  mainWrapper.style.display = 'flex';
    }

    /* ========== 模板管理 ========== */
    async function loadTemplates(page = 1) {
        if (page) state.template.page = page;
        const tbody = document.getElementById('tmTemplateBody');
        if (!tbody) return;
        tbody.innerHTML = `<tr><td colspan="5" class="tm-empty">加载中...</td></tr>`;
        try {
            const params = new URLSearchParams({
                page: state.template.page,
                page_size: PAGE_SIZE,
            });
            if (state.template.keyword) params.append('keyword', state.template.keyword);
            const resp = await fetch(`${API_BASE}/asr/pacs_report_template?${params}`);
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            const result = await resp.json();
            const list = result.data || result.items || result.list || (Array.isArray(result) ? result : []);
            const total = result.total || result.count || list.length;
            state.template.list = list;
            state.template.total = total;
            renderTemplates(list);
            renderPagination('tmTemplatePagination', state.template.page, total, PAGE_SIZE, loadTemplates);
        } catch (err) {
            console.error('加载模板失败:', err);
            tbody.innerHTML = `<tr><td colspan="5" class="tm-empty">加载失败：${escapeHtml(err.message)}</td></tr>`;
        }
    }

    function renderTemplates(list) {
        const tbody = document.getElementById('tmTemplateBody');
        if (!list || list.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" class="tm-empty">暂无数据</td></tr>`;
            return;
        }
        tbody.innerHTML = list.map(item => `
            <tr data-id="${item.id}">
                <td>${escapeHtml(item.id)}</td>
                <td><strong>${escapeHtml(item.check_item || '-')}</strong></td>
                <td>${renderPreviewCell(item.report_template)}</td>
                <td>${item.group_id != null ? escapeHtml(item.group_id) : '-1'}</td>
                <td>
                    <div class="tm-actions">
                        <button class="btn btn-outline btn-sm tm-edit-tpl" data-id="${item.id}">✏️ 编辑</button>
                        <button class="btn btn-danger-outline btn-sm tm-del-tpl" data-id="${item.id}">🗑 删除</button>
                    </div>
                </td>
            </tr>
        `).join('');

        $$('.tm-edit-tpl', tbody).forEach(btn => {
            btn.onclick = () => {
                const id = parseInt(btn.dataset.id);
                const item = state.template.list.find(x => x.id === id);
                if (item) openTemplateForm(item);
            };
        });
        $$('.tm-del-tpl', tbody).forEach(btn => {
            btn.onclick = async () => {
                const id = parseInt(btn.dataset.id);
                const item = state.template.list.find(x => x.id === id);
                const ok = await confirmDialog('删除模板', `确定要删除模板 #${id}【${item?.check_item || ''}】吗？\n此操作不可恢复。`);
                if (!ok) return;
                await deleteTemplate(id);
            };
        });
        bindCellToggles(tbody);
    }

    async function deleteTemplate(id) {
        try {
            const resp = await fetch(`${API_BASE}/asr/pacs_report_template/${id}`, { method: 'DELETE' });
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            toast('删除成功', 'success');
            state.checkItemOptions = null;   // ★ 新增
            loadTemplates(state.template.page);
        } catch (err) {
            toast('删除失败：' + err.message, 'error');
        }
    }

    function openTemplateForm(data) {
        const isEdit = !!data;
        const title = isEdit ? `编辑模板 #${data.id}` : '新增模板';
        const fields = [
            { key: 'check_item',      label: '检查项目', type: 'text', required: true, placeholder: '例如：腹部脏器（肝、胆、胰、脾）', hint: '必填，与语音识别结果中的检查项目名称一致' },
            { key: 'report_template', label: '报告模板', type: 'textarea', placeholder: '请输入报告模板内容...', hint: '可留空，后续可在词条中补充' },
            { key: 'group_id',        label: '分组ID',  type: 'number', placeholder: '-1', defaultVal: -1, hint: '多个检查项目共用同一模板时使用相同分组ID，默认为 -1' },
        ];
        openFormModal(title, fields, data || {}, async (values) => {
            const payload = {
                check_item: values.check_item.trim(),
                report_template: values.report_template,
                group_id: parseInt(values.group_id) || -1,
            };
            try {
                const url = isEdit
                    ? `${API_BASE}/asr/pacs_report_template/${data.id}`
                    : `${API_BASE}/asr/pacs_report_template`;
                const method = isEdit ? 'PUT' : 'POST';
                const resp = await fetch(url, {
                    method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                });
                if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
                const result = await resp.json().catch(() => ({}));
                if (result.success === false) throw new Error(result.message || '保存失败');

                toast(isEdit ? '模板已更新' : '模板已创建', 'success');
                loadTemplates(isEdit ? state.template.page : 1);
                preloadAllCheckItems(); // 刷新检查项目列表
                state.checkItemOptions = null;   // ★ 让下次打开词条表单时重新拉取
                return true;
            } catch (err) {
                toast('保存失败：' + err.message, 'error');
                return false;
            }
        });
    }

    /* ========== 词条管理 ========== */
    async function loadEntries(page = 1) {
        if (page) state.entry.page = page;
        const tbody = document.getElementById('tmEntryBody');
        if (!tbody) return;
        tbody.innerHTML = `<tr><td colspan="7" class="tm-empty">加载中...</td></tr>`;
        try {
            const params = new URLSearchParams({
                page: state.entry.page,
                page_size: PAGE_SIZE,
            });
            if (state.entry.keyword) params.append('keyword', state.entry.keyword);
            const resp = await fetch(`${API_BASE}/asr/pacs_report_entry?${params}`);
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            const result = await resp.json();
            const list = result.data || result.items || result.list || (Array.isArray(result) ? result : []);
            const total = result.total || result.count || list.length;
            state.entry.list = list;
            state.entry.total = total;
            renderEntries(list);
            renderPagination('tmEntryPagination', state.entry.page, total, PAGE_SIZE, loadEntries);
        } catch (err) {
            console.error('加载词条失败:', err);
            tbody.innerHTML = `<tr><td colspan="7" class="tm-empty">加载失败：${escapeHtml(err.message)}</td></tr>`;
        }
    }

    function renderEntries(list) {
        const tbody = document.getElementById('tmEntryBody');
        if (!list || list.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="tm-empty">暂无数据</td></tr>`;
            return;
        }
        tbody.innerHTML = list.map(item => `
            <tr data-id="${item.id}">
                <td>${escapeHtml(item.id)}</td>
                <td><span class="tm-tag">${escapeHtml(item.keyword || '-')}</span></td>
                <td>${escapeHtml(item.check_item || '-')}</td>
                <td>${item.check_item_id != null ? escapeHtml(item.check_item_id) : '-'}</td>
                <td>${renderPreviewCell(item.seen)}</td>
                <td>${renderPreviewCell(item.prompt)}</td>
                <td>
                    <div class="tm-actions">
                        <button class="btn btn-outline btn-sm tm-edit-entry" data-id="${item.id}">✏️ 编辑</button>
                        <button class="btn btn-danger-outline btn-sm tm-del-entry" data-id="${item.id}">🗑 删除</button>
                    </div>
                </td>
            </tr>
        `).join('');

        $$('.tm-edit-entry', tbody).forEach(btn => {
            btn.onclick = () => {
                const id = parseInt(btn.dataset.id);
                const item = state.entry.list.find(x => x.id === id);
                if (item) openEntryForm(item);
            };
        });
        $$('.tm-del-entry', tbody).forEach(btn => {
            btn.onclick = async () => {
                const id = parseInt(btn.dataset.id);
                const item = state.entry.list.find(x => x.id === id);
                const ok = await confirmDialog('删除词条', `确定要删除词条 #${id}【${item?.keyword || ''}】吗？`);
                if (!ok) return;
                await deleteEntry(id);
            };
        });
        bindCellToggles(tbody);
    }

    async function deleteEntry(id) {
        try {
            const resp = await fetch(`${API_BASE}/asr/pacs_report_entry/${id}`, { method: 'DELETE' });
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            toast('删除成功', 'success');
            loadEntries(state.entry.page);
        } catch (err) {
            toast('删除失败：' + err.message, 'error');
        }
    }

    async function openEntryForm(data) {
        const isEdit = !!data;
        const title = isEdit ? `编辑词条 #${data.id}` : '新增词条';

        /* ★ 先加载检查项目列表 */
        const options = await loadCheckItemOptions();

        /* 构建下拉选项：value 用名称（保证与 DB 中 check_item 字段一致），
           同时携带 id 供联动使用 */
        const selectOptions = options.map(o => ({
            value: o.check_item,
            label: `${o.check_item}　（ID: ${o.id}）`,
            id: o.id,
        }));

        const fields = [
            { key: 'keyword', label: '关键字', type: 'text', required: true,
              placeholder: '例如：胆囊 或者 胆囊1胆囊炎',
              hint: '必填，医生口述中触发此词条的识别关键字, 如果有多个关键字请用 【数字 1】分隔' },

            // ★ 检查项目：改为下拉
            { key: 'check_item', label: '检查项目', type: 'select', required: true,
              options: selectOptions,
              linkedField: 'check_item_id',   // ★ 选中后自动同步到 check_item_id
              hint: '从已有检查项目中选择，选中后会自动填充"检查项目ID"' },

            // ★ 检查项目ID：改为只读，由上面下拉自动带入
            { key: 'check_item_id', label: '检查项目ID', type: 'number',
              placeholder: '选择检查项目后自动填充',
              readonly: true,
              hint: '与模板表 id 关联，由所选的检查项目自动带入，无需手动填写' },

            { key: 'seen', label: '超声所见应补充内容', type: 'textarea',
              placeholder: '例如：胆囊大小 {} mm，囊壁光滑，囊内透声尚可，肝区回声稍增粗。',
              hint: '使用 {} 作为占位符，将用医生口述的数值替换（如"胆囊4*7"→"{}"→"4*7"）' },

            { key: 'prompt', label: '超声提示应补充内容', type: 'textarea',
              placeholder: '例如：胆囊增大（{} mm），建议结合临床。',
              hint: '使用 {} 作为占位符' },
        ];

        openFormModal(title, fields, data || {}, async (values) => {
            const payload = {
                keyword: values.keyword.trim(),
                seen: values.seen,
                prompt: values.prompt,
                check_item_id: values.check_item_id ? parseInt(values.check_item_id) : null,
                check_item: values.check_item,
            };
            try {
                const url = isEdit
                    ? `${API_BASE}/asr/pacs_report_entry/${data.id}`
                    : `${API_BASE}/asr/pacs_report_entry`;
                const method = isEdit ? 'PUT' : 'POST';
                const resp = await fetch(url, {
                    method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                });
                if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
                const result = await resp.json().catch(() => ({}));
                if (result.success === false) throw new Error(result.message || '保存失败');
                toast(isEdit ? '词条已更新' : '词条已创建', 'success');
                loadEntries(isEdit ? state.entry.page : 1);
                return true;
            } catch (err) {
                toast('保存失败：' + err.message, 'error');
                return false;
            }
        });
    }

    /* ========== 预加载检查项目（用于 datalist 自动补全） ========== */
    async function preloadAllCheckItems() {
        try {
            const resp = await fetch(`${API_BASE}/asr/pacs_report_template?page=1&page_size=100`);
            if (!resp.ok) return;
            const result = await resp.json();
            const list = result.data || result.items || result.list || (Array.isArray(result) ? result : []);
            const items = [...new Set(list.map(x => x.check_item).filter(Boolean))];
            state.checkItems = items;
            let dl = document.getElementById('tmCheckItemList');
            if (!dl) {
                dl = document.createElement('datalist');
                dl.id = 'tmCheckItemList';
                document.body.appendChild(dl);
            }
            dl.innerHTML = items.map(x => `<option value="${escapeHtml(x)}"></option>`).join('');
        } catch (e) {
            /* 静默失败：不影响主功能 */
            console.warn('预加载检查项目失败:', e);
        }
    }

    /* ========== 加载检查项目选项（用于词条表单下拉） ========== */
    async function loadCheckItemOptions(forceReload) {
        if (!forceReload && state.checkItemOptions && state.checkItemOptions.length > 0) {
            return state.checkItemOptions;
        }
        try {
            const resp = await fetch(`${API_BASE}/asr/check_item_options`);
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            const result = await resp.json();
            const list = result.data || result.items || (Array.isArray(result) ? result : []);
            state.checkItemOptions = list
                .map(x => ({ id: x.id, check_item: x.check_item || '' }))
                .filter(x => x.check_item);  // 过滤掉空名称
            return state.checkItemOptions;
        } catch (err) {
            console.warn('加载检查项目选项失败:', err);
            state.checkItemOptions = [];
            return [];
        }
    }

    /* ========== 通用表单弹窗（大文本编辑器优化版） ========== */
    function openFormModal(title, fields, data, onSubmit) {
        var overlay = document.createElement('div');
        overlay.className = 'tm-form-overlay';
        overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.5);z-index:99999;display:flex;align-items:center;justify-content:center;padding:20px;box-sizing:border-box;';

        var box = document.createElement('div');
        box.className = 'tm-form-box';
        box.style.cssText = 'background:#fff;border-radius:14px;max-width:680px;width:100%;max-height:88vh;display:flex;flex-direction:column;box-shadow:0 20px 60px rgba(0,0,0,0.3);overflow:hidden;font-family:inherit;transition:max-width 0.2s,width 0.2s;';

        /* 标题栏 */
        var header = document.createElement('div');
        header.style.cssText = 'padding:14px 20px;border-bottom:1px solid #e2e5ea;display:flex;justify-content:space-between;align-items:center;flex-shrink:0;';
        header.innerHTML =
            '<h3 style="margin:0;font-size:1rem;color:#1a1d23;font-weight:700;">' + escapeHtml(title) + '</h3>' +
            '<button class="tm-close" style="background:transparent;border:none;font-size:22px;cursor:pointer;color:#949aa5;padding:0 6px;line-height:1;">✕</button>';

        /* 表单体 */
        var body = document.createElement('div');
        body.className = 'tm-form-body';
        body.style.cssText = 'padding:16px 20px;overflow-y:auto;flex:1;';

        var inputStyle = 'width:100%;padding:8px 10px;border:1.5px solid #e2e5ea;border-radius:8px;font-size:0.85rem;font-family:inherit;outline:none;box-sizing:border-box;background:#f9fafb;transition:all 0.2s;color:#1a1d23;';

        fields.forEach(function(f) {
            var val = (data[f.key] !== undefined && data[f.key] !== null)
                ? data[f.key]
                : (f.defaultVal !== undefined ? f.defaultVal : '');
            val = val === null || val === undefined ? '' : String(val);

            /* ---------- textarea：带工具栏 & 全屏 ---------- */
            if (f.type === 'textarea') {
                var group = document.createElement('div');
                group.className = 'tm-field-group';

                var head = document.createElement('div');
                head.className = 'tm-field-head';
                head.innerHTML =
                    '<span class="tm-field-label">' +
                        escapeHtml(f.label) + (f.required ? ' <span style="color:#d14343;">*</span>' : '') +
                    '</span>' +
                    '<span class="tm-field-meta">' +
                        '<span class="tm-char-counter">' + val.length + ' 字</span>' +
                        '<button type="button" class="tm-btn-expand" title="放大编辑区域">⛶ 全屏</button>' +
                    '</span>';

                var ta = document.createElement('textarea');
                ta.setAttribute('data-key', f.key);
                if (f.required) ta.required = true;
                ta.placeholder = f.placeholder || '';
                ta.value = val;
                ta.style.cssText = inputStyle + 'min-height:180px;resize:vertical;line-height:1.7;';

                group.appendChild(head);
                group.appendChild(ta);
                if (f.hint) {
                    var hint = document.createElement('div');
                    hint.className = 'tm-editor-hint';
                    hint.textContent = f.hint;
                    group.appendChild(hint);
                }
                body.appendChild(group);

                /* 字数统计 */
                var counter = head.querySelector('.tm-char-counter');
                ta.addEventListener('input', function() {
                    counter.textContent = ta.value.length + ' 字';
                });

                /* 全屏切换 */
                var fsBtn = head.querySelector('.tm-btn-expand');
                var origMinH = '180px';
                fsBtn.onclick = function() {
                    var isFs = ta.classList.contains('tm-ta-fs');
                    if (isFs) {
                        ta.classList.remove('tm-ta-fs');
                        ta.style.minHeight = origMinH;
                        fsBtn.innerHTML = '⛶ 全屏';
                        // 若无其它全屏 textarea，则还原弹窗尺寸
                        if (!body.querySelector('textarea.tm-ta-fs')) {
                            overlay.classList.remove('tm-has-fs');
                        }
                    } else {
                        ta.classList.add('tm-ta-fs');
                        ta.style.minHeight = '';
                        fsBtn.innerHTML = '⛶ 还原';
                        overlay.classList.add('tm-has-fs');
                    }
                    // 让 textarea 立即聚焦，方便继续输入
                    setTimeout(function() { ta.focus(); }, 30);
                };
                return;
            }

            /* ---------- select 下拉框 ---------- */
            if (f.type === 'select') {
                var group = document.createElement('div');
                group.className = 'tm-field-group';

                var head = document.createElement('div');
                head.className = 'tm-field-head';
                head.innerHTML =
                    '<span class="tm-field-label">' +
                        escapeHtml(f.label) + (f.required ? ' <span style="color:#d14343;">*</span>' : '') +
                    '</span>';
                group.appendChild(head);

                var sel = document.createElement('select');
                sel.setAttribute('data-key', f.key);
                if (f.required) sel.required = true;
                sel.style.cssText = inputStyle + 'height:38px;cursor:pointer;';

                // 空选项
                var emptyOpt = document.createElement('option');
                emptyOpt.value = '';
                emptyOpt.textContent = '— 请选择检查项目 —';
                sel.appendChild(emptyOpt);

                // 填充选项
                (f.options || []).forEach(function(opt) {
                    var o = document.createElement('option');
                    o.value = opt.value;
                    o.textContent = opt.label;
                    if (opt.id !== undefined && opt.id !== null) o.dataset.id = opt.id;
                    sel.appendChild(o);
                });

                // 若当前值不在选项里（项目可能已被删/改名），补一条"原值"选项，避免编辑时丢失
                if (val) {
                    var matched = (f.options || []).some(function(opt) {
                        return String(opt.value) === String(val);
                    });
                    if (!matched) {
                        var customOpt = document.createElement('option');
                        customOpt.value = val;
                        customOpt.textContent = val + '（原值，未在列表）';
                        sel.appendChild(customOpt);
                    }
                    sel.value = val;
                }

                // ★ 联动：选中后把对应 id 填到 linkedField 指定的输入框
                if (f.linkedField) {
                    sel.addEventListener('change', function() {
                        var linkedInp = body.querySelector('[data-key="' + f.linkedField + '"]');
                        if (!linkedInp) return;
                        var opt = sel.options[sel.selectedIndex];
                        var id = (opt && opt.dataset && opt.dataset.id) ? opt.dataset.id : '';
                        linkedInp.value = id;
                    });
                }

                group.appendChild(sel);
                if (f.hint) {
                    var hint = document.createElement('div');
                    hint.className = 'tm-editor-hint';
                    hint.textContent = f.hint;
                    group.appendChild(hint);
                }
                body.appendChild(group);
                return;
            }

            /* ---------- 其它输入类型 ---------- */
            var group = document.createElement('div');
            group.className = 'tm-field-group';

            var readonlyAttr  = f.readonly ? 'readonly ' : '';
            var readonlyStyle = f.readonly ? 'background:#f0f1f3;color:#949aa5;cursor:not-allowed;' : '';

            var inputHtml = '';
            var commonAttr = 'data-key="' + f.key + '" ' +
                             (f.required ? 'required ' : '') +
                             'placeholder="' + escapeHtml(f.placeholder || '') + '" ';
            if (f.type === 'number') {
                inputHtml = '<input type="number" ' + commonAttr + readonlyAttr +
                            'value="' + escapeHtml(val) + '" style="' + inputStyle + readonlyStyle + '">';
            } else {
                var listAttr = f.list ? ('list="' + f.list + '" ') : '';
                inputHtml = '<input type="text" ' + commonAttr + readonlyAttr +
                            'value="' + escapeHtml(val) + '" ' + listAttr +
                            'autocomplete="off" style="' + inputStyle + readonlyStyle + '">';
            }

            group.innerHTML =
                '<div class="tm-field-head">' +
                    '<span class="tm-field-label">' +
                        escapeHtml(f.label) + (f.required ? ' <span style="color:#d14343;">*</span>' : '') +
                    '</span>' +
                '</div>' +
                inputHtml +
                (f.hint ? ('<div class="tm-editor-hint">' + escapeHtml(f.hint) + '</div>') : '');
            body.appendChild(group);
        });

        /* 底部按钮 */
        var footer = document.createElement('div');
        footer.style.cssText = 'padding:12px 20px;border-top:1px solid #e2e5ea;display:flex;justify-content:flex-end;gap:8px;flex-shrink:0;background:#f9fafb;';
        footer.innerHTML =
            '<button class="tm-cancel" style="padding:7px 18px;border-radius:6px;border:1.5px solid #e2e5ea;background:#fff;cursor:pointer;font-family:inherit;font-size:0.85rem;">取消</button>' +
            '<button class="tm-submit" style="padding:7px 18px;border-radius:6px;border:none;background:#1a6fb5;color:#fff;cursor:pointer;font-family:inherit;font-size:0.85rem;font-weight:600;">💾 保存</button>';

        box.appendChild(header);
        box.appendChild(body);
        box.appendChild(footer);
        overlay.appendChild(box);
        document.body.appendChild(overlay);

        /* 焦点样式 */
        $$('input, textarea, select', body).forEach(function(inp) {
            if (inp.hasAttribute('readonly')) return;   // ★ readonly 不加聚焦效果
            inp.onfocus = function() {
                inp.style.borderColor = '#1a6fb5';
                inp.style.background = '#fff';
                inp.style.boxShadow = '0 0 0 3px rgba(26,111,181,0.08)';
            };
            inp.onblur = function() {
                if (inp.classList.contains('tm-ta-fs')) return;
                inp.style.borderColor = '#e2e5ea';
                inp.style.background = '#f9fafb';
                inp.style.boxShadow = 'none';
            };
        });

        /* 关闭逻辑 */
        var close = function() {
            if (overlay.parentNode) overlay.remove();
            // 解除可能残留的全屏类
            overlay.classList.remove('tm-has-fs');
        };
        $('.tm-close', box).onclick = close;
        $('.tm-cancel', box).onclick = close;
        overlay.onclick = function(e) { if (e.target === overlay) close(); };

        /* 提交 */
        $('.tm-submit', box).onclick = function() {
            var values = {};
            var valid = true;
            fields.forEach(function(f) {
                var inp = $('[data-key="' + f.key + '"]', body);
                if (!inp) return;
                var v = inp.value;
                if (f.required && !v.replace(/^\s+|\s+$/g, '')) {
                    inp.style.borderColor = '#d14343';
                    inp.style.boxShadow = '0 0 0 3px rgba(209,67,67,0.1)';
                    valid = false;
                }
                values[f.key] = v;
            });
            if (!valid) { toast('请填写必填项', 'warning'); return; }

            var result = onSubmit(values);
            if (result && typeof result.then === 'function') {
                result.then(function(ok) { if (ok !== false) close(); });
            } else if (result !== false) {
                close();
            }
        };
    }
    /* ========== 分页 ========== */
    function renderPagination(containerId, current, total, pageSize, onPageChange) {
        const container = document.getElementById(containerId);
        if (!container) return;
        const totalPages = Math.max(1, Math.ceil(total / pageSize));
        if (totalPages <= 1) { container.innerHTML = ''; return; }

        let html = `<button ${current <= 1 ? 'disabled' : ''} data-page="${current - 1}">◀</button>`;
        const maxBtns = 7;
        let start = Math.max(1, current - 3);
        let end = Math.min(totalPages, start + maxBtns - 1);
        if (end - start < maxBtns - 1) start = Math.max(1, end - maxBtns + 1);

        if (start > 1) {
            html += `<button data-page="1">1</button>`;
            if (start > 2) html += `<span style="padding:3px 6px;color:#949aa5;">...</span>`;
        }
        for (let i = start; i <= end; i++) {
            html += `<button class="${i === current ? 'active' : ''}" data-page="${i}">${i}</button>`;
        }
        if (end < totalPages) {
            if (end < totalPages - 1) html += `<span style="padding:3px 6px;color:#949aa5;">...</span>`;
            html += `<button data-page="${totalPages}">${totalPages}</button>`;
        }
        html += `<button ${current >= totalPages ? 'disabled' : ''} data-page="${current + 1}">▶</button>`;
        container.innerHTML = html;

        $$('button[data-page]', container).forEach(btn => {
            btn.onclick = () => {
                const p = parseInt(btn.dataset.page);
                if (!isNaN(p) && p >= 1 && p <= totalPages) onPageChange(p);
            };
        });
    }

    /* ========== 事件绑定 ========== */
    function bindEvents() {
        const openBtn = document.getElementById('tmOpenBtn');
        if (openBtn) openBtn.onclick = showTemplateView;

        const backBtn = document.getElementById('tmBackBtn');
        if (backBtn) backBtn.onclick = showMainView;

        /* Tab 切换 */
        $$('.tm-tab').forEach(tab => {
            tab.onclick = () => {
                const target = tab.dataset.tab;
                state.activeTab = target;
                $$('.tm-tab').forEach(t => t.classList.toggle('active', t === tab));
                $$('.tm-panel').forEach(p => p.style.display = 'none');
                const panel = document.getElementById('tmPanel-' + target);
                if (panel) panel.style.display = 'block';
                if (target === 'template') loadTemplates(1);
                else loadEntries(1);
            };
        });

        /* 模板搜索/刷新/新增 */
        const tplSearch = document.getElementById('tmTemplateSearch');
        if (tplSearch) {
            let t;
            tplSearch.oninput = () => {
                clearTimeout(t);
                t = setTimeout(() => {
                    state.template.keyword = tplSearch.value.trim();
                    loadTemplates(1);
                }, 300);
            };
        }
        const tplRefresh = document.getElementById('tmRefreshTemplateBtn');
        if (tplRefresh) tplRefresh.onclick = () => loadTemplates(state.template.page);
        const tplAdd = document.getElementById('tmAddTemplateBtn');
        if (tplAdd) tplAdd.onclick = () => openTemplateForm(null);

        /* 词条搜索/刷新/新增 */
        const entrySearch = document.getElementById('tmEntrySearch');
        if (entrySearch) {
            let t;
            entrySearch.oninput = () => {
                clearTimeout(t);
                t = setTimeout(() => {
                    state.entry.keyword = entrySearch.value.trim();
                    loadEntries(1);
                }, 300);
            };
        }
        const entryRefresh = document.getElementById('tmRefreshEntryBtn');
        if (entryRefresh) entryRefresh.onclick = () => loadEntries(state.entry.page);
        const entryAdd = document.getElementById('tmAddEntryBtn');
        if (entryAdd) entryAdd.onclick = () => openEntryForm(null);

        /* ESC 关闭子页面（仅当没有弹窗时） */
        document.addEventListener('keydown', (e) => {
            if (e.key !== 'Escape') return;
            if (!templateView || templateView.style.display === 'none') return;
            if (document.querySelector('.tm-form-overlay')) return; // 有弹窗时不关闭页面
            showMainView();
        });
    }

    /* ========== 初始化 ========== */
    function init() {
        if (!templateView) {
            console.warn('templateManageView 未找到，跳过初始化');
            return;
        }
        bindEvents();
        preloadAllCheckItems();
        console.log('✅ 模板管理模块初始化完成');
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();