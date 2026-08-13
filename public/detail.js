/**
 * Segunda Mente V4.0 — detail.js
 * Modal de detalhe de um conteúdo: visualização completa, marcar revisado,
 * reprocessar e excluir.
 */
window.SM = window.SM || {};

window.SM.Detail = (function () {
    const { apiFetch, showToast, formatDate, escapeHtml, typeIcon, typeLabel } = window.SM;

    let currentId = null;

    function $(id) { return document.getElementById(id); }

    const INTENT_LABELS = {
        estudar: 'Estudar',
        assistir: 'Assistir',
        lembrar: 'Lembrar',
        ideia: 'Ideia',
        referencia: 'Referência',
        executar: 'Executar',
    };

    const STATUS_LABELS = {
        pending: '🕓 Pendente',
        processing: '⏳ Processando',
        processed: null, // usa is_reviewed em vez disso
        error: '⚠️ Erro no processamento',
    };

    function render(content) {
        const c = content;
        const tags = (c.tags || []).map((t) => `<span class="tag">#${escapeHtml(t)}</span>`).join('');
        const projects = (c.projects || []).join(' • ');
        const bodyText = c.original_text || '';
        const transcription = c.transcription || c.extracted_text || '';
        const statusLine = STATUS_LABELS[c.status] || (c.is_reviewed ? '✅ Revisado' : '⬜ Não revisado');

        let html = '';

        if (c.thumbnail_url) {
            html += `<img class="detail-thumbnail" src="${escapeHtml(c.thumbnail_url)}" alt="">`;
        }

        html += `<div class="detail-title"><span>${typeIcon(c.content_type)}</span><span>${escapeHtml(c.title || 'Sem título')}</span></div>`;

        html += `<div class="detail-meta-row">Categoria: ${escapeHtml([c.category, c.subcategory].filter(Boolean).join(' > ') || 'Sem categoria')}</div>`;
        html += `<div class="detail-meta-row">Capturado: ${escapeHtml(formatDate(c.created_at))}</div>`;
        if (c.intent) html += `<div class="detail-meta-row">Intenção: ${escapeHtml(INTENT_LABELS[c.intent] || c.intent)}</div>`;
        html += `<div class="detail-meta-row">Status: ${statusLine}</div>`;

        if (c.summary) {
            html += `
                <div class="detail-block">
                    <div class="detail-block-title">── Resumo ──</div>
                    <div class="detail-text">${escapeHtml(c.summary)}</div>
                </div>`;
        }

        html += `
            <button class="btn-primary btn-block" id="btn-generate-prompt">🤖 Gerar Prompt para Executar</button>
            <div id="generate-prompt-section" class="generate-prompt-section hidden">
                <div class="detail-block-title">── Prompt Gerado ──</div>
                <div class="generate-prompt-box" id="generate-prompt-box"></div>
                <button class="btn-secondary btn-block" id="btn-copy-prompt">📋 Copiar Prompt</button>
            </div>`;

        if (bodyText && c.content_type === 'text') {
            html += `
                <div class="detail-block">
                    <div class="detail-block-title">── Nota original ──</div>
                    <div class="detail-text">${escapeHtml(bodyText)}</div>
                </div>`;
        }

        if (tags) {
            html += `
                <div class="detail-block">
                    <div class="detail-block-title">── Tags ──</div>
                    <div>${tags}</div>
                </div>`;
        }

        if (projects) {
            html += `
                <div class="detail-block">
                    <div class="detail-block-title">── Projetos ──</div>
                    <div class="detail-text">${escapeHtml(projects)}</div>
                </div>`;
        }

        if (transcription) {
            const label = c.transcription ? 'Transcrição' : 'Texto extraído';
            html += `
                <div class="detail-block">
                    <div class="detail-block-title">── ${label} ──</div>
                    <div class="detail-transcription" id="detail-transcription">${escapeHtml(transcription)}</div>
                    <button class="detail-expand-btn" id="btn-expand-transcription">▼ Expandir completa</button>
                </div>`;
        }

        if (c.source_url) {
            html += `
                <div class="detail-block">
                    <div class="detail-block-title">── Fonte ──</div>
                    <a class="detail-source-link" href="${escapeHtml(c.source_url)}" target="_blank" rel="noopener">🔗 ${escapeHtml(c.source_url)}</a>
                </div>`;
        }

        html += `
            <button class="btn-primary btn-block" id="btn-mark-reviewed" ${c.is_reviewed ? 'disabled' : ''}>
                ${c.is_reviewed ? '✅ Já revisado' : '✅ Marcar revisado'}
            </button>
            <button class="btn-secondary btn-block" id="btn-reprocess">🔄 Reprocessar</button>
        `;

        $('detail-body').innerHTML = html;

        const expandBtn = $('btn-expand-transcription');
        if (expandBtn) {
            expandBtn.addEventListener('click', () => {
                const box = $('detail-transcription');
                const expanded = box.classList.toggle('expanded');
                expandBtn.textContent = expanded ? '▲ Recolher' : '▼ Expandir completa';
            });
        }

        $('btn-mark-reviewed').addEventListener('click', markReviewed);
        $('btn-reprocess').addEventListener('click', reprocess);
        $('btn-generate-prompt').addEventListener('click', generatePrompt);
        $('btn-copy-prompt').addEventListener('click', copyPrompt);
    }

    async function open(id) {
        currentId = id;
        $('detail-overlay').classList.remove('hidden');
        $('detail-body').innerHTML = '<p class="empty-hint">Carregando...</p>';
        try {
            const content = await apiFetch(`/contents/${id}`);
            render(content);
        } catch (e) {
            $('detail-body').innerHTML = `<p class="empty-hint">Erro ao carregar: ${escapeHtml(e.message)}</p>`;
        }
    }

    function close() {
        $('detail-overlay').classList.add('hidden');
        currentId = null;
    }

    async function markReviewed() {
        if (!currentId) return;
        try {
            await apiFetch(`/contents/${currentId}`, {
                method: 'PATCH',
                body: JSON.stringify({ is_reviewed: true }),
            });
            showToast('Marcado como revisado.', 'success');
            open(currentId);
            if (window.SM.Library) window.SM.Library.refresh();
        } catch (e) {
            showToast('Erro ao marcar como revisado: ' + e.message, 'error');
        }
    }

    async function reprocess() {
        if (!currentId) return;
        showToast('Reprocessando...', 'info');
        try {
            await apiFetch(`/process/${currentId}`, { method: 'POST' });
            showToast('Reprocessado com sucesso.', 'success');
            open(currentId);
            if (window.SM.Library) window.SM.Library.refresh();
        } catch (e) {
            showToast('Erro ao reprocessar: ' + e.message, 'error');
        }
    }

    async function generatePrompt() {
        if (!currentId) return;
        const btn = $('btn-generate-prompt');
        const section = $('generate-prompt-section');
        const box = $('generate-prompt-box');

        btn.disabled = true;
        btn.textContent = 'Gerando prompt...';
        section.classList.remove('hidden');
        box.textContent = 'Gerando prompt...';

        try {
            const data = await apiFetch('/generate-prompt', {
                method: 'POST',
                body: JSON.stringify({ content_id: currentId }),
            });
            box.textContent = data.prompt;
        } catch (e) {
            section.classList.add('hidden');
            showToast('Erro ao gerar prompt: ' + e.message, 'error');
        } finally {
            btn.disabled = false;
            btn.textContent = '🤖 Gerar Prompt para Executar';
        }
    }

    async function copyPrompt() {
        const box = $('generate-prompt-box');
        const text = box ? box.textContent : '';
        if (!text) return;
        try {
            await navigator.clipboard.writeText(text);
            showToast('Prompt copiado!', 'success');
        } catch (e) {
            showToast('Não foi possível copiar. Selecione e copie manualmente.', 'error');
        }
    }

    async function remove() {
        if (!currentId) return;
        if (!window.confirm('Excluir este conteúdo permanentemente?')) return;
        try {
            await apiFetch(`/contents/${currentId}`, { method: 'DELETE' });
            showToast('Conteúdo excluído.', 'success');
            close();
            if (window.SM.Library) window.SM.Library.refresh();
        } catch (e) {
            showToast('Erro ao excluir: ' + e.message, 'error');
        }
    }

    function init() {
        $('btn-detail-back').addEventListener('click', close);
        $('btn-detail-delete').addEventListener('click', remove);
        $('detail-overlay').addEventListener('click', (e) => {
            if (e.target.id === 'detail-overlay') close();
        });
    }

    return { init, open, close };
})();
