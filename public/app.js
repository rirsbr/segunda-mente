/**
 * Segunda Mente V4.0 — app.js
 * Núcleo: namespace global SM, roteamento entre telas, utilitários
 * compartilhados (fetch da API, toasts, formatação de datas etc).
 */
window.SM = (function () {
    const API_BASE = '/api';

    const TYPE_ICONS = {
        text: '📝',
        link: '🔗',
        audio: '🎙',
        video: '🎥',
        pdf: '📄',
        image: '📷',
    };

    const TYPE_LABELS = {
        text: 'Texto',
        link: 'Link',
        audio: 'Áudio',
        video: 'Vídeo',
        pdf: 'PDF',
        image: 'Imagem',
    };

    // ============ FETCH DA API ============
    async function apiFetch(path, options = {}) {
        const res = await fetch(API_BASE + path, {
            headers: options.body && !(options.body instanceof FormData)
                ? { 'Content-Type': 'application/json', ...(options.headers || {}) }
                : (options.headers || {}),
            ...options,
        });

        let data = null;
        try {
            data = await res.json();
        } catch (e) {
            data = null;
        }

        if (!res.ok) {
            const message = (data && (data.detail || data.message)) || `Erro ${res.status}`;
            throw new Error(typeof message === 'string' ? message : JSON.stringify(message));
        }
        return data;
    }

    // ============ TOAST ============
    function showToast(message, type = 'info', duration = 3500) {
        const container = document.getElementById('toast-container');
        if (!container) return;
        const el = document.createElement('div');
        el.className = `toast toast-${type}`;
        el.textContent = message;
        container.appendChild(el);
        setTimeout(() => {
            el.style.transition = 'opacity 0.3s';
            el.style.opacity = '0';
            setTimeout(() => el.remove(), 300);
        }, duration);
    }

    // ============ FORMATAÇÃO ============
    function timeAgo(dateStr) {
        if (!dateStr) return '';
        const date = new Date(dateStr);
        const diffMs = Date.now() - date.getTime();
        const diffSec = Math.floor(diffMs / 1000);

        if (diffSec < 60) return 'agora';
        const diffMin = Math.floor(diffSec / 60);
        if (diffMin < 60) return `${diffMin}min`;
        const diffH = Math.floor(diffMin / 60);
        if (diffH < 24) return `${diffH}h`;
        const diffD = Math.floor(diffH / 24);
        if (diffD < 30) return `${diffD}d`;
        const diffMonth = Math.floor(diffD / 30);
        if (diffMonth < 12) return `${diffMonth}mês`;
        return date.toLocaleDateString('pt-BR');
    }

    function formatDate(dateStr) {
        if (!dateStr) return '';
        return new Date(dateStr).toLocaleDateString('pt-BR', {
            day: '2-digit', month: '2-digit', year: 'numeric',
        });
    }

    function escapeHtml(str) {
        if (str === null || str === undefined) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function typeIcon(type) {
        return TYPE_ICONS[type] || '📦';
    }

    function typeLabel(type) {
        return TYPE_LABELS[type] || type || '';
    }

    // ============ FILTRO DE PERÍODO ============
    // Usado pelos dropdowns de período da Busca e da Biblioteca — calcula
    // `from`/`to` (ISO) no frontend a partir de uma chave de período.
    const PERIOD_DAYS = {
        '7d': 7,
        '1m': 30,
        '3m': 90,
        '6m': 180,
        '1y': 365,
    };

    function computePeriodRange(value) {
        const days = PERIOD_DAYS[value];
        if (!days) return { from: '', to: '' };
        const to = new Date();
        const from = new Date();
        from.setDate(from.getDate() - days);
        return { from: from.toISOString(), to: to.toISOString() };
    }

    // ============ ROTEAMENTO ENTRE TELAS ============
    function showScreen(name) {
        document.querySelectorAll('.screen').forEach((el) => {
            el.classList.toggle('hidden', el.dataset.screen !== name);
        });
        document.querySelectorAll('.nav-btn').forEach((btn) => {
            btn.classList.toggle('active', btn.dataset.nav === name);
        });
        window.scrollTo(0, 0);
        window.location.hash = name;
    }

    function initNav() {
        document.querySelectorAll('.nav-btn').forEach((btn) => {
            btn.addEventListener('click', () => showScreen(btn.dataset.nav));
        });

        const initial = (window.location.hash || '').replace('#', '');
        showScreen(['capture', 'search', 'library'].includes(initial) ? initial : 'capture');
    }

    // ============ SERVICE WORKER ============
    function registerServiceWorker() {
        if ('serviceWorker' in navigator) {
            window.addEventListener('load', () => {
                navigator.serviceWorker.register('/sw.js').catch(() => {
                    /* silencioso — PWA é progressivo */
                });
            });
        }
    }

    // ============ COMPARTILHAMENTO (Web Share Target — GET) ============
    /**
     * manifest.json declara share_target com method "GET" e action "/#share",
     * mapeando title/text/url. O navegador então abre o app numa URL como
     * "/?title=...&text=...&url=...#share" — os dados chegam como query
     * string comum (window.location.search), então na inicialização do app
     * é só ler esses parâmetros e capturar automaticamente:
     *   - se vier "url"  → POST /api/capture/link
     *   - senão, se vier "text" → POST /api/capture/text
     */
    function cleanUrlParams(params) {
        const query = params.toString();
        const newUrl = window.location.pathname + (query ? `?${query}` : '') + window.location.hash;
        window.history.replaceState({}, '', newUrl);
    }

    async function handleShareTarget() {
        const params = new URLSearchParams(window.location.search);
        const sharedUrl = (params.get('url') || '').trim();
        const sharedText = (params.get('text') || '').trim();

        if (!sharedUrl && !sharedText) return;

        params.delete('title');
        params.delete('text');
        params.delete('url');
        cleanUrlParams(params);

        try {
            if (sharedUrl) {
                await apiFetch('/capture/link', {
                    method: 'POST',
                    body: JSON.stringify({ url: sharedUrl }),
                });
            } else {
                await apiFetch('/capture/text', {
                    method: 'POST',
                    body: JSON.stringify({ text: sharedText }),
                });
            }
            showToast('Capturado!', 'success');
            if (window.SM.Capture && window.SM.Capture.loadRecent) window.SM.Capture.loadRecent();
        } catch (e) {
            showToast('Erro ao capturar conteúdo compartilhado: ' + e.message, 'error');
        }
    }

    // ============ DETECÇÃO DE URL NA CAPTURA DE TEXTO ============
    /**
     * Quando o usuário cola algo no campo de captura e o texto colado é,
     * inteiro, uma URL (https://...), captura automaticamente como link —
     * sem precisar clicar em CAPTURAR.
     */
    async function captureDetectedLink(url, textarea) {
        showToast('Link detectado! Capturando...', 'info');
        try {
            await apiFetch('/capture/link', {
                method: 'POST',
                body: JSON.stringify({ url }),
            });
            showToast('Capturado!', 'success');
            if (textarea) textarea.value = '';
            if (window.SM.Capture && window.SM.Capture.loadRecent) window.SM.Capture.loadRecent();
        } catch (e) {
            showToast('Erro ao capturar link: ' + e.message, 'error');
        }
    }

    function initPasteUrlDetection() {
        const textarea = document.getElementById('capture-textarea');
        if (!textarea) return;

        textarea.addEventListener('paste', (e) => {
            const clipboard = e.clipboardData || window.clipboardData;
            if (!clipboard) return;
            const pasted = (clipboard.getData('text') || '').trim();
            if (!pasted) return;

            if (/^https?:\/\/[^\s]+$/i.test(pasted)) {
                e.preventDefault();
                captureDetectedLink(pasted, textarea);
            }
            // Texto misto (URL + palavras) ou texto puro: deixa o paste
            // normal acontecer, o usuário revisa e clica em CAPTURAR.
        });
    }

    function init() {
        initNav();
        registerServiceWorker();

        if (window.SM.Capture && window.SM.Capture.init) window.SM.Capture.init();
        if (window.SM.Search && window.SM.Search.init) window.SM.Search.init();
        if (window.SM.Library && window.SM.Library.init) window.SM.Library.init();
        if (window.SM.Detail && window.SM.Detail.init) window.SM.Detail.init();

        initPasteUrlDetection();
        handleShareTarget();
    }

    document.addEventListener('DOMContentLoaded', init);

    return {
        apiFetch,
        showToast,
        timeAgo,
        formatDate,
        escapeHtml,
        typeIcon,
        typeLabel,
        showScreen,
        computePeriodRange,
    };
})();
