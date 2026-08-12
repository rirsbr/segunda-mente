/**
 * Segunda Mente V4.0 — Service Worker
 * Cacheia apenas assets estáticos (app shell). Chamadas /api/* sempre vão
 * direto para a rede — nunca servir dados desatualizados da base.
 *
 * Também implementa o lado do Service Worker do Web Share Target API:
 * quando outro app (YouTube, Instagram, Chrome...) compartilha conteúdo
 * com a Segunda Mente, o navegador faz um POST multipart/form-data para
 * "/share" (ver share_target no manifest.json). Como não há servidor
 * capaz de processar esse POST diretamente (é uma rota estática), o SW
 * intercepta essa requisição, extrai os dados do FormData, guarda no
 * IndexedDB e redireciona para /share.html — uma página normal que lê
 * esse payload e chama a API de captura.
 */
const CACHE_NAME = 'segunda-mente-v5';
const STATIC_ASSETS = [
    '/',
    '/index.html',
    '/styles.css',
    '/app.js',
    '/capture.js',
    '/search.js',
    '/library.js',
    '/detail.js',
    '/share.html',
    '/share.js',
    '/manifest.json',
    '/icons/icon-192.png',
    '/icons/icon-512.png',
];

const SHARE_DB_NAME = 'segunda-mente-share';
const SHARE_STORE_NAME = 'pending';
const SHARE_RECORD_KEY = 'latest';

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => cache.addAll(STATIC_ASSETS))
            .then(() => self.skipWaiting())
    );
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
        ).then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', (event) => {
    const url = new URL(event.request.url);

    // Web Share Target: POST multipart/form-data para /share
    if (event.request.method === 'POST' && url.pathname === '/share') {
        event.respondWith(handleShareTarget(event));
        return;
    }

    // API: sempre rede, nunca cache
    if (url.pathname.startsWith('/api/')) {
        return;
    }

    // Apenas GET é cacheável — outros métodos (ex: POST de formulários) vão direto pra rede
    if (event.request.method !== 'GET') {
        return;
    }

    // Assets estáticos: cache-first com fallback de rede
    event.respondWith(
        caches.match(event.request).then((cached) => {
            if (cached) return cached;
            return fetch(event.request).then((response) => {
                if (response && response.status === 200) {
                    const clone = response.clone();
                    caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
                }
                return response;
            }).catch(() => cached);
        })
    );
});

async function handleShareTarget(event) {
    try {
        const formData = await event.request.formData();
        const payload = {
            title: formData.get('title') || '',
            text: formData.get('text') || '',
            url: formData.get('url') || '',
            files: formData.getAll('files').filter((f) => f && typeof f === 'object' && f.size > 0),
        };
        await saveSharedPayload(payload);
    } catch (err) {
        // Se der errado, share.html vai simplesmente não encontrar payload
        // e mostrar "nada para capturar" — nunca deixamos o POST travado.
    }
    return Response.redirect('/share.html', 303);
}

function openShareDb() {
    return new Promise((resolve, reject) => {
        const req = indexedDB.open(SHARE_DB_NAME, 1);
        req.onupgradeneeded = () => {
            if (!req.result.objectStoreNames.contains(SHARE_STORE_NAME)) {
                req.result.createObjectStore(SHARE_STORE_NAME);
            }
        };
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => reject(req.error);
    });
}

async function saveSharedPayload(payload) {
    const db = await openShareDb();
    return new Promise((resolve, reject) => {
        const tx = db.transaction(SHARE_STORE_NAME, 'readwrite');
        tx.objectStore(SHARE_STORE_NAME).put(payload, SHARE_RECORD_KEY);
        tx.oncomplete = () => resolve();
        tx.onerror = () => reject(tx.error);
    });
}
