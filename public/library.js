/**
 * Segunda Mente V4.0 — library.js
 * Tela de Biblioteca: filtros por tipo/categoria, ordenação, scroll infinito.
 */
window.SM = window.SM || {};

window.SM.Library = (function () {
    const { apiFetch, showToast, timeAgo, escapeHtml, typeIcon } = window.SM;

    const PAGE_SIZE = 20;
    const TYPES = ['text', 'link', 'audio', 'video', 'pdf', 'image'];

    let state = {
        type: '',
        category: '',
        sort: 'created_at',
        order: 'desc',
        offset: 0,
        loading: false,
        finished: false,
    };

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

    async function loadStats() {
        try {
            const stats = await apiFetch('/stats');
            $('library-summary').textContent =
                `${stats.total} conteúdos • ${stats.unreviewed} não vistos`;
            renderTypeFilters(stats.by_type || {});
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

    function init() {
        $('library-category').addEventListener('change', (e) => {
            state.category = e.target.value;
            resetAndLoad();
        });

        $('library-sort').addEventListener('change', (e) => {
            const [sort, order] = e.target.value.split(':');
            state.sort = sort;
            state.order = order;
            resetAndLoad();
        });

        // Recarrega dados sempre que o usuário navega para a Biblioteca
        document.querySelectorAll('.nav-btn[data-nav="library"]').forEach((btn) => {
            btn.addEventListener('click', () => {
                loadStats();
                resetAndLoad();
            });
        });

        initInfiniteScroll();
        loadStats();
        loadPage(false);
    }

    return { init, refresh: () => { loadStats(); resetAndLoad(); } };
})();
