/**
 * Segunda Mente V4.0 — share.js
 * Página de destino do Web Share Target (public/share.html).
 *
 * O navegador faz um POST multipart/form-data direto para "/share" (ver
 * share_target no manifest.json). Esse POST é interceptado pelo
 * Service Worker (sw.js), que guarda os dados compartilhados no IndexedDB
 * e redireciona (303) para esta página, que roda em contexto de página
 * normal (com acesso a fetch/DOM) e finaliza a captura chamando a API.
 *
 * Fluxo: compartilhou → capturado → toast de confirmação → volta pro app.
 */
(function () {
    const DB_NAME = 'segunda-mente-share';
    const STORE_NAME = 'pending';
    const RECORD_KEY = 'latest';

    function openDb() {
        return new Promise((resolve, reject) => {
            const req = indexedDB.open(DB_NAME, 1);
            req.onupgradeneeded = () => {
                if (!req.result.objectStoreNames.contains(STORE_NAME)) {
                    req.result.createObjectStore(STORE_NAME);
                }
            };
            req.onsuccess = () => resolve(req.result);
            req.onerror = () => reject(req.error);
        });
    }

    async function takeSharedPayload() {
        try {
            const db = await openDb();
            return await new Promise((resolve, reject) => {
                const tx = db.transaction(STORE_NAME, 'readwrite');
                const store = tx.objectStore(STORE_NAME);
                const getReq = store.get(RECORD_KEY);
                getReq.onsuccess = () => {
                    const data = getReq.result;
                    store.delete(RECORD_KEY);
                    resolve(data || null);
                };
                getReq.onerror = () => reject(getReq.error);
            });
        } catch (e) {
            return null;
        }
    }

    function isUrl(str) {
        if (!str) return false;
        return /^https?:\/\/[^\s]+$/i.test(str.trim());
    }

    function extractUrl(str) {
        if (!str) return null;
        const match = str.match(/https?:\/\/[^\s]+/i);
        return match ? match[0] : null;
    }

    async function apiFetch(path, options) {
        const res = await fetch('/api' + path, options);
        let data = null;
        try { data = await res.json(); } catch (e) { /* corpo vazio */ }
        if (!res.ok) {
            const msg = (data && (data.detail || data.message)) || `Erro ${res.status}`;
            throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
        }
        return data;
    }

    function setStatus(msg) {
        const el = document.getElementById('share-status');
        if (el) el.textContent = msg;
    }

    function captureUrl(url) {
        return apiFetch('/capture/link', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url }),
        });
    }

    function captureText(text) {
        return apiFetch('/capture/text', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text }),
        });
    }

    function captureFile(file) {
        const fd = new FormData();
        fd.append('file', file, file.name || 'arquivo-compartilhado');
        return apiFetch('/capture/file', { method: 'POST', body: fd });
    }

    function goHome(params) {
        const query = params.toString();
        setTimeout(() => {
            window.location.replace('/' + (query ? `?${query}` : ''));
        }, 1200);
    }

    async function run() {
        setStatus('Recebendo conteúdo compartilhado...');
        const payload = await takeSharedPayload();

        if (!payload) {
            setStatus('Nenhum conteúdo compartilhado encontrado.');
            goHome(new URLSearchParams({ shared: 'empty' }));
            return;
        }

        const title = (payload.title || '').trim();
        const text = (payload.text || '').trim();
        const url = (payload.url || '').trim();
        const files = (payload.files || []).filter((f) => f && f.size);

        const captured = [];
        const errors = [];

        const directUrl = isUrl(url) ? url : (extractUrl(url) || extractUrl(text));

        try {
            if (directUrl) {
                setStatus('Capturando link...');
                const data = await captureUrl(directUrl);
                captured.push(data.title || directUrl);
            } else if (text) {
                setStatus('Capturando texto...');
                const combined = title ? `${title}\n\n${text}` : text;
                const data = await captureText(combined);
                captured.push(data.title || 'nota');
            } else if (title) {
                setStatus('Capturando...');
                const data = await captureText(title);
                captured.push(data.title || title);
            }
        } catch (e) {
            errors.push(e.message);
        }

        for (const file of files) {
            try {
                setStatus(`Capturando ${file.name || 'arquivo'}...`);
                const data = await captureFile(file);
                captured.push(data.title || file.name);
            } catch (e) {
                errors.push(e.message);
            }
        }

        const params = new URLSearchParams();
        if (!directUrl && !text && !title && !files.length) {
            setStatus('Nada para capturar.');
            params.set('shared', 'empty');
        } else if (captured.length && !errors.length) {
            setStatus(`✅ Capturado: ${captured.join(', ')}`);
            params.set('shared', 'success');
            params.set('title', captured[0]);
        } else if (captured.length && errors.length) {
            setStatus(`⚠️ Capturado parcialmente (${captured.length}). Alguns itens falharam.`);
            params.set('shared', 'partial');
            params.set('title', captured[0]);
        } else {
            setStatus('❌ Não foi possível capturar o conteúdo compartilhado.');
            params.set('shared', 'error');
        }

        goHome(params);
    }

    document.addEventListener('DOMContentLoaded', run);
})();
