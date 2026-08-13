/**
 * Segunda Mente V4.0 — search.js
 * Tela de Busca: pergunta em linguagem natural (/api/ask) + filtros (/api/search),
 * busca por voz, resultados com relevância visual e agrupamento por tema.
 */
window.SM = window.SM || {};

window.SM.Search = (function () {
    const { apiFetch, showToast, timeAgo, escapeHtml, typeIcon } = window.SM;

    function $(id) { return document.getElementById(id); }

    // ============ DESTAQUE DE TERMOS ============
    function escapeRegex(str) {
        return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    function highlightTerms(text, terms) {
        const escaped = escapeHtml(text || '');
        const validTerms = (terms || []).filter((t) => t && t.length >= 3);
        if (!validTerms.length) return escaped;
        const pattern = validTerms.map((t) => escapeRegex(escapeHtml(t))).join('|');
        if (!pattern) return escaped;
        const regex = new RegExp(`(${pattern})`, 'gi');
        return escaped.replace(regex, '<mark class="search-highlight">$1</mark>');
    }

    // ============ RELEVÂNCIA ============
    function relevanceBucket(score) {
        if (score >= 70) return 'high';
        if (score >= 40) return 'medium';
        return 'low';
    }

    // ============ CARDS ============
    function cardHtml(c, terms) {
        const tags = (c.tags || []).slice(0, 5)
            .map((t) => `<span class="tag">#${escapeHtml(t)}</span>`).join('');
        const categoryLine = [c.category, c.subcategory].filter(Boolean).join(' > ');
        const score = typeof c.relevance_score === 'number' ? c.relevance_score : 0;
        const bucket = relevanceBucket(score);
        const titleHtml = highlightTerms(c.title || 'Sem título', terms);
        const summaryHtml = c.summary ? highlightTerms(c.summary, terms) : '';

        return `
            <div class="content-card" data-id="${c.id}">
                <div class="relevance-row">
                    <div class="relevance-bar"><div class="relevance-fill ${bucket}" style="width:${score}%"></div></div>
                    <span class="relevance-badge ${bucket}">${score}% relevante</span>
                </div>
                <div class="content-card-title">
                    <span>${typeIcon(c.content_type)}</span>
                    <span>${titleHtml}</span>
                </div>
                <div class="content-card-meta">
                    <span>${escapeHtml(categoryLine || 'Sem categoria')}</span>
                    <span>•</span>
                    <span>${timeAgo(c.created_at)}</span>
                </div>
                ${summaryHtml ? `<div class="content-card-summary">${summaryHtml}</div>` : ''}
                ${tags ? `<div class="content-card-tags">${tags}</div>` : ''}
            </div>
        `;
    }

    // ============ AGRUPAMENTO POR TEMA (categoria) ============
    function groupResults(results) {
        const groups = new Map();
        results.forEach((r) => {
            const key = r.category || 'Sem categoria';
            if (!groups.has(key)) groups.set(key, []);
            groups.get(key).push(r);
        });
        return [...groups.entries()]
            .map(([category, items]) => {
                const sorted = items.slice().sort((a, b) => (b.relevance_score || 0) - (a.relevance_score || 0));
                return {
                    category,
                    items: sorted,
                    maxScore: Math.max(...sorted.map((i) => i.relevance_score || 0)),
                };
            })
            .sort((a, b) => b.maxScore - a.maxScore);
    }

    function renderResults(container, results, terms) {
        if (!results || !results.length) {
            container.innerHTML = '<p class="empty-hint">Nenhum resultado encontrado.</p>';
            return;
        }

        const groups = groupResults(results);
        const singleGroup = groups.length <= 1;

        container.innerHTML = groups.map((g) => {
            const cardsHtml = g.items.map((c) => cardHtml(c, terms)).join('');
            if (singleGroup) {
                return `<div class="content-list">${cardsHtml}</div>`;
            }
            const count = g.items.length;
            return `
                <div class="result-group">
                    <div class="result-group-title">${escapeHtml(g.category)} (${count} resultado${count > 1 ? 's' : ''})</div>
                    <div class="content-list">${cardsHtml}</div>
                </div>
            `;
        }).join('');

        container.querySelectorAll('.content-card').forEach((el) => {
            el.addEventListener('click', () => {
                if (window.SM.Detail) window.SM.Detail.open(el.dataset.id);
            });
        });
    }

    // ============ BUSCA ============
    async function runSearch() {
        const query = $('search-input').value.trim();
        if (!query) {
            showToast('Digite uma pergunta ou termo de busca.', 'error');
            return;
        }

        const type = $('filter-type').value;
        const category = $('filter-category').value;
        const terms = query.split(/\s+/).filter(Boolean);

        const answerSection = $('ask-answer-section');
        const answerEl = $('ask-answer');
        const resultsEl = $('search-results');

        resultsEl.innerHTML = '<p class="empty-hint">Buscando...</p>';
        answerSection.classList.add('hidden');

        // Resposta em linguagem natural via IA (concisa, com pontuação de relevância)
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

        // Resultados filtráveis via busca híbrida, com relevância/agrupamento
        try {
            const params = new URLSearchParams({ q: query, limit: '20' });
            if (type) params.set('type', type);
            if (category) params.set('category', category);

            const searchData = await apiFetch(`/search?${params.toString()}`);
            renderResults(resultsEl, searchData.results, terms);
        } catch (e) {
            resultsEl.innerHTML = `<p class="empty-hint">Erro na busca: ${escapeHtml(e.message)}</p>`;
        }
    }

    // ============ BUSCA POR VOZ (Web Speech API) ============
    function initVoiceSearch() {
        const btn = $('btn-voice-search');
        if (!btn) return;

        const SpeechRecognitionImpl = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognitionImpl) {
            btn.classList.add('hidden');
            return;
        }

        const recognition = new SpeechRecognitionImpl();
        recognition.lang = 'pt-BR';
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;

        let listening = false;

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            $('search-input').value = transcript;
            runSearch();
        };
        recognition.onerror = () => {
            showToast('Não foi possível reconhecer a fala. Tente novamente.', 'error');
        };
        recognition.onend = () => {
            listening = false;
            btn.classList.remove('recording');
        };

        btn.addEventListener('click', () => {
            if (listening) {
                recognition.stop();
                return;
            }
            try {
                recognition.start();
                listening = true;
                btn.classList.add('recording');
                showToast('Ouvindo... fale sua busca.', 'info');
            } catch (e) {
                showToast('Não foi possível iniciar o microfone.', 'error');
            }
        });
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

        initVoiceSearch();
    }

    return { init };
})();
