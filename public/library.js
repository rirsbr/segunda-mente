/**
 * Segunda Mente V4.0 — library.js
 * Tela de Biblioteca: filtros por tipo/categoria (com subcategorias), tags
 * em nuvem, ordenação, scroll infinito e manutenção da base (processar
 * pendentes / reclassificar tudo).
 */
window.SM = window.SM || {};

window.SM.Library = (function () {
    const { apiFetch, showToast, timeAgo, escapeHtml, typeIcon, computePeriodRange } = window.SM;

    const PAGE_SIZE = 20;
    const TYPES = ['text', 'link', 'audio', 'video', 'pdf', 'image'];

    // Mesma fonte da verdade que api/_lib/config.py:CATEGORY_GROUPS.
    const CATEGORY_GROUPS = {
        'IA': [
            'IA - Geração de Vídeo',
            'IA - Geração de Imagem',
            'IA - Geração de Texto',
            'IA - Agentes e Automação',
            'IA - Ferramentas',
        ],
        'Marketing Digital': ['Marketing Digital'],
        'Negócios e Empreendedorismo': ['Negócios e Empreendedorismo'],
        'Programação': ['Programação'],
        'Trabalho - Petrobras': ['Trabalho - Petrobras'],
        'Casa e Pessoal': ['Casa e Pessoal'],
        'Entretenimento': ['Entretenimento'],
        'Outro': ['Outro'],
    };

    let state = {
        type: '',
        categoryGroup: '',
        category: '',
        tag: '',
        period: '',
        sort: 'created_at',
        order: 'desc',
        offset: 0,
        loading: false,
        finished: false,
    };

    let lastByCategory = {};
    let lastTopTags = [];

    function $(id) { return document.getElementById(id); }

    function cardHtml(c) {
        const tags = (c.tags || []).slice(0, 6)
            .map((t) => `<span class="tag">#${escapeHtml(t)}</span>`).join('');
        const categoryLine = [c.category, c.subcategory].filter(Boolean).join(' > ');
        const reviewIcon = c.is_reviewed ? '✅ visto' : '⬜ não visto';
        return `
            <div class="content-card" data-id="${c.id}">
                <div class="content-card-title">
                    <span>${typeIcon(c.content_type)}</span>
                    <span>${escapeHtml(c.title || 'Processando...')}</span>
                </div>
                <div class="content-card-meta">
                    <span>${escapeHtml(categoryLine || 'Sem categoria')}</span>
                    <span>•</span>
                    <span>${timeAgo(c.created_at)}</span>
                    <span>•</span>
                    <span>${reviewIcon}</span>
                </div>
                ${tags ? `<div class="content-card-tags">${tags}</div>` : ''}
            </div>
        `;
    }

    function bindCardClicks(container) {
        container.querySelectorAll('.content-card').forEach((el) => {
            el.addEventListener('click', () => {
                if (window.SM.Detail) window.SM.Detail.open(el.dataset.id);
            });
        });
    }

    // ============ STATS / FILTROS ============
    async function loadStats() {
        try {
            const stats = await apiFetch('/stats');
            $('library-summary').textContent =
                `${stats.total} conteúdos • ${stats.unreviewed} não vistos • ${stats.pending} pendentes`;
            lastByCategory = stats.by_category || {};
            lastTopTags = stats.top_tags || [];
            renderTypeFilters(stats.by_type || {});
            renderCategoryChips();
            renderSubcategoryChips();
            renderTagCloud();
        } catch (e) {
            $('library-summary').textContent = '';
        }
    }

    function renderTypeFilters(byType) {
        const container = $('library-type-filters');
        const allCount = Object.values(byType).reduce((a, b) => a + b, 0);
        const buttons = [`<button class="type-filter-btn ${!state.type ? 'active' : ''}" data-type="">Todos ${allCount}</button>`];
        TYPES.forEach((t) => {
            const count = byType[t] || 0;
            buttons.push(
                `<button class="type-filter-btn ${state.type === t ? 'active' : ''}" data-type="${t}">${typeIcon(t)} ${count}</button>`
            );
        });
        container.innerHTML = buttons.join('');
        container.querySelectorAll('.type-filter-btn').forEach((btn) => {
            btn.addEventListener('click', () => {
                state.type = btn.dataset.type;
                container.querySelectorAll('.type-filter-btn').forEach((b) => b.classList.remove('active'));
                btn.classList.add('active');
                resetAndLoad();
            });
        });
    }

    // ============ CATEGORIAS (chips + drill-down de subcategoria) ============
    function renderCategoryChips() {
        const container = $('library-category-chips');
        const totalAll = Object.values(lastByCategory).reduce((a, b) => a + b, 0);

        const chips = [
            `<button class="category-chip ${!state.categoryGroup ? 'active' : ''}" data-group="">Todos<span class="chip-count">${totalAll}</span></button>`,
        ];
        Object.keys(CATEGORY_GROUPS).forEach((group) => {
            const cats = CATEGORY_GROUPS[group];
            const count = cats.reduce((sum, c) => sum + (lastByCategory[c] || 0), 0);
            chips.push(
                `<button class="category-chip ${state.categoryGroup === group ? 'active' : ''}" data-group="${escapeHtml(group)}">${escapeHtml(group)}<span class="chip-count">${count}</span></button>`
            );
        });

        container.innerHTML = chips.join('');
        container.querySelectorAll('.category-chip').forEach((btn) => {
            btn.addEventListener('click', () => onCategoryGroupClick(btn.dataset.group));
        });
    }

    function onCategoryGroupClick(group) {
        const cats = CATEGORY_GROUPS[group] || [];

        if (!group) {
            state.categoryGroup = '';
            state.category = '';
        } else if (cats.length > 1) {
            // Grupo com subcategorias (ex: "IA") — mostra o drill-down,
            // ainda não filtra por uma subcategoria específica.
            state.categoryGroup = group;
            state.category = '';
        } else {
            // Grupo com uma categoria só — filtra direto, sem subfiltro.
            state.categoryGroup = group;
            state.category = cats[0] || '';
        }

        renderCategoryChips();
        renderSubcategoryChips();
        resetAndLoad();
    }

    function renderSubcategoryChips() {
        const container = $('library-subcategory-chips');
        const cats = CATEGORY_GROUPS[state.categoryGroup] || [];

        if (!state.categoryGroup || cats.length <= 1) {
            container.classList.add('hidden');
            container.innerHTML = '';
            return;
        }

        const prefix = `${state.categoryGroup} - `;
        const chips = cats.map((c) => {
            const count = lastByCategory[c] || 0;
            const label = c.startsWith(prefix) ? c.slice(prefix.length) : c;
            return `<button class="category-chip ${state.category === c ? 'active' : ''}" data-category="${escapeHtml(c)}">${escapeHtml(label)}<span class="chip-count">${count}</span></button>`;
        });

        container.innerHTML = chips.join('');
        container.classList.remove('hidden');
        container.querySelectorAll('.category-chip').forEach((btn) => {
            btn.addEventListener('click', () => {
                state.category = state.category === btn.dataset.category ? '' : btn.dataset.category;
                renderSubcategoryChips();
                resetAndLoad();
            });
        });
    }

    // ============ NUVEM DE TAGS ============
    function renderTagCloud() {
        const container = $('library-tag-cloud');
        if (!lastTopTags.length) {
            container.innerHTML = '<p class="empty-hint">Nenhuma tag ainda.</p>';
            return;
        }

        const counts = lastTopTags.map((t) => t.count);
        const max = Math.max(...counts);
        const min = Math.min(...counts);
        const range = Math.max(max - min, 1);

        function sizeClass(count) {
            const ratio = (count - min) / range;
            if (ratio >= 0.75) return 'size-4';
            if (ratio >= 0.5) return 'size-3';
            if (ratio >= 0.25) return 'size-2';
            return 'size-1';
        }

        container.innerHTML = lastTopTags.map((t) => `
            <button class="tag-cloud-pill ${sizeClass(t.count)} ${state.tag === t.name ? 'active' : ''}" data-tag="${escapeHtml(t.name)}">
                #${escapeHtml(t.name)}
            </button>
        `).join('');

        container.querySelectorAll('.tag-cloud-pill').forEach((btn) => {
            btn.addEventListener('click', () => {
                state.tag = state.tag === btn.dataset.tag ? '' : btn.dataset.tag;
                renderTagCloud();
                resetAndLoad();
            });
        });
    }

    // ============ LISTAGEM ============
    async function loadPage(append) {
        if (state.loading || state.finished) return;
        state.loading = true;
        $('library-loading').classList.remove('hidden');

        const resultsEl = $('library-results');
        if (!append) resultsEl.innerHTML = '<p class="empty-hint">Carregando...</p>';

        try {
            const params = new URLSearchParams({
                sort: state.sort,
                order: state.order,
                limit: String(PAGE_SIZE),
                offset: String(state.offset),
            });
            if (state.type) params.set('type', state.type);
            if (state.category) params.set('category', state.category);
            if (state.tag) params.set('tag', state.tag);
            if (state.period) {
                const { from, to } = computePeriodRange(state.period);
                if (from) params.set('from', from);
                if (to) params.set('to', to);
            }

            const data = await apiFetch(`/contents?${params.toString()}`);
            const results = data.results || [];

            if (!append) resultsEl.innerHTML = '';
            if (!results.length && !append) {
                resultsEl.innerHTML = '<p class="empty-hint">Nenhum conteúdo encontrado.</p>';
            } else {
                const html = results.map(cardHtml).join('');
                resultsEl.insertAdjacentHTML('beforeend', html);
                bindCardClicks(resultsEl);
            }

            state.offset += results.length;
            if (results.length < PAGE_SIZE) state.finished = true;
        } catch (e) {
            if (!append) resultsEl.innerHTML = `<p class="empty-hint">Erro ao carregar: ${escapeHtml(e.message)}</p>`;
            showToast('Erro ao carregar biblioteca: ' + e.message, 'error');
        } finally {
            state.loading = false;
            $('library-loading').classList.add('hidden');
        }
    }

    function resetAndLoad() {
        state.offset = 0;
        state.finished = false;
        loadPage(false);
    }

    function initInfiniteScroll() {
        window.addEventListener('scroll', () => {
            const screen = document.getElementById('screen-library');
            if (screen.classList.contains('hidden')) return;
            const nearBottom = window.innerHeight + window.scrollY >= document.body.scrollHeight - 300;
            if (nearBottom) loadPage(true);
        });
    }

    // ============ MANUTENÇÃO DA BASE (lotes de 10) ============
    async function runBatchOperation({ button, endpoint, labelVerb }) {
        button.disabled = true;
        const progressWrap = $('admin-progress-wrap');
        const progressFill = $('admin-progress-fill');
        const progressLabel = $('admin-progress-label');
        progressWrap.classList.remove('hidden');
        progressFill.style.width = '0%';
        progressLabel.textContent = `Iniciando ${labelVerb}...`;

        let offset = 0;
        let total = 0;
        let okCount = 0;
        let failCount = 0;

        try {
            // Loop de lotes: cada chamada processa até 10 itens e informa se
            // já terminou — a UI vai atualizando a barra a cada resposta.
            while (true) {
                const data = await apiFetch(`${endpoint}?offset=${offset}&limit=10`, { method: 'POST' });
                total = data.total || 0;
                okCount += (data.processed || []).length;
                failCount += (data.failed || []).length;
                offset = typeof data.next_offset === 'number' ? data.next_offset : offset + 10;

                const pct = total ? Math.min(100, Math.round((offset / total) * 100)) : 100;
                progressFill.style.width = `${pct}%`;
                progressLabel.textContent = total
                    ? `${Math.min(offset, total)}/${total} — ${okCount} ok, ${failCount} falharam`
                    : 'Nada para processar.';

                if (!total || data.done) break;
            }

            showToast(
                `${labelVerb}: concluído! ${okCount} processados${failCount ? `, ${failCount} falharam` : ''}.`,
                failCount ? 'info' : 'success'
            );
        } catch (e) {
            showToast(`Erro em "${labelVerb}": ` + e.message, 'error');
        } finally {
            button.disabled = false;
            setTimeout(() => progressWrap.classList.add('hidden'), 2500);
            loadStats();
            resetAndLoad();
        }
    }

    function initAdminButtons() {
        $('btn-process-pending').addEventListener('click', () => {
            runBatchOperation({
                button: $('btn-process-pending'),
                endpoint: '/process/pending',
                labelVerb: 'Processar pendentes',
            });
        });

        $('btn-reclassify-all').addEventListener('click', () => {
            runBatchOperation({
                button: $('btn-reclassify-all'),
                endpoint: '/reclassify/all',
                labelVerb: 'Reclassificar tudo',
            });
        });
    }

    function init() {
        $('library-sort').addEventListener('change', (e) => {
            const [sort, order] = e.target.value.split(':');
            state.sort = sort;
            state.order = order;
            resetAndLoad();
        });

        $('library-period').addEventListener('change', (e) => {
            state.period = e.target.value;
            resetAndLoad();
        });

        // Recarrega dados sempre que o usuário navega para a Biblioteca
        document.querySelectorAll('.nav-btn[data-nav="library"]').forEach((btn) => {
            btn.addEventListener('click', () => {
                loadStats();
                resetAndLoad();
            });
        });

        initAdminButtons();
        initInfiniteScroll();
        loadStats();
        loadPage(false);
    }

    return { init, refresh: () => { loadStats(); resetAndLoad(); } };
})();
