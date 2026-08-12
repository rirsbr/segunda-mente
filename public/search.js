/**
 * Segunda Mente V4.0 — search.js
 * Tela de Busca: pergunta em linguagem natural (/api/ask) + filtros (/api/search).
 */
window.SM = window.SM || {};

window.SM.Search = (function () {
    const { apiFetch, showToast, timeAgo, escapeHtml, typeIcon } = window.SM;

    function $(id) { return document.getElementById(id); }

    function renderResults(container, results) {
        if (!results || !results.length) {
            container.innerHTML = '<p class="empty-hint">Nenhum resultado encontrado.</p>';
            return;
        }
        container.innerHTML = results.map(cardHtml).join('');
        container.querySelectorAll('.content-card').forEach((el) => {
            el.addEventListener('click', () => {
                if (window.SM.Detail) window.SM.Detail.open(el.dataset.id);
            });
        });
    }

    function cardHtml(c) {
        const tags = (c.tags || []).slice(0, 5)
            .map((t) => `<span class="tag">#${escapeHtml(t)}</span>`).join('');
        const categoryLine = [c.category, c.subcategory].filter(Boolean).join(' > ');
        return `
            <div class="content-card" data-id="${c.id}">
                <div class="content-card-title">
                    <span>${typeIcon(c.content_type)}</span>
                    <span>${escapeHtml(c.title || 'Sem título')}</span>
                </div>
                <div class="content-card-meta">
                    <span>${escapeHtml(categoryLine || 'Sem categoria')}</span>
                    <span>•</span>
                    <span>${timeAgo(c.created_at)}</span>
                </div>
                ${c.summary ? `<div class="content-card-summary">${escapeHtml(c.summary)}</div>` : ''}
                ${tags ? `<div class="content-card-tags">${tags}</div>` : ''}
            </div>
        `;
    }

    async function runSearch() {
        const query = $('search-input').value.trim();
        if (!query) {
            showToast('Digite uma pergunta ou termo de busca.', 'error');
            return;
        }

        const type = $('filter-type').value;
        const category = $('filter-category').value;

        const answerSection = $('ask-answer-section');
        const answerEl = $('ask-answer');
        const resultsEl = $('search-results');

        resultsEl.innerHTML = '<p class="empty-hint">Buscando...</p>';
        answerSection.classList.add('hidden');

        // Resposta em linguagem natural via IA
        try {
            const askData = await apiFetch('/ask', {
                method: 'POST',
                body: JSON.stringify({ question: query }),
            });
            answerEl.textContent = askData.answer;
            answerSection.classList.remove('hidden');
        } catch (e) {
            // Falha no /ask não deve impedir a busca filtrada
        }

        // Resultados filtráveis via busca híbrida
        try {
            const params = new URLSearchParams({ q: query, limit: '20' });
            if (type) params.set('type', type);
            if (category) params.set('category', category);

            const searchData = await apiFetch(`/search?${params.toString()}`);
            renderResults(resultsEl, searchData.results);
        } catch (e) {
            resultsEl.innerHTML = `<p class="empty-hint">Erro na busca: ${escapeHtml(e.message)}</p>`;
        }
    }

    function init() {
        $('search-form').addEventListener('submit', (e) => {
            e.preventDefault();
            runSearch();
        });
        $('filter-type').addEventListener('change', () => {
            if ($('search-input').value.trim()) runSearch();
        });
        $('filter-category').addEventListener('change', () => {
            if ($('search-input').value.trim()) runSearch();
        });
    }

    return { init };
})();
