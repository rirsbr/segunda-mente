/**
 * Segunda Mente V4.0 — capture.js
 * Tela de Captura: texto, link, arquivo, foto e áudio gravado.
 */
window.SM = window.SM || {};

window.SM.Capture = (function () {
    const { apiFetch, showToast, timeAgo, escapeHtml, typeIcon } = window.SM;

    let mediaRecorder = null;
    let audioChunks = [];
    let recordingStart = null;
    let recordingTimer = null;
    let pendingLinkMode = false;

    function $(id) { return document.getElementById(id); }

    function detectContentType(text) {
        const urlRegex = /https?:\/\/[^\s]+/g;
        const urls = text.match(urlRegex);
        if (urls && urls.length === 1 && text.trim() === urls[0]) {
            return { type: 'link', url: urls[0] };
        }
        return { type: 'text', text };
    }

    // ============ RECENTES ============
    async function loadRecent() {
        const list = $('recent-list');
        try {
            const data = await apiFetch('/contents?limit=5&sort=created_at&order=desc');
            const results = data.results || [];
            if (!results.length) {
                list.innerHTML = '<p class="empty-hint">Nada capturado ainda.</p>';
                return;
            }
            list.innerHTML = results.map((c) => `
                <div class="recent-item" data-id="${c.id}">
                    <span class="recent-item-icon">${typeIcon(c.content_type)}</span>
                    <span class="recent-item-title">${escapeHtml(c.title || 'Processando...')}</span>
                    <span class="recent-item-status">${escapeHtml(statusLabel(c.status))}</span>
                    <span class="recent-item-time">${timeAgo(c.created_at)}</span>
                </div>
            `).join('');

            list.querySelectorAll('.recent-item').forEach((el) => {
                el.addEventListener('click', () => {
                    if (window.SM.Detail) window.SM.Detail.open(el.dataset.id);
                });
            });
        } catch (e) {
            list.innerHTML = '<p class="empty-hint">Não foi possível carregar as capturas recentes.</p>';
        }
    }

    function statusLabel(status) {
        const map = { pending: 'pendente', processing: 'processando', processed: 'ok', error: 'erro' };
        return map[status] || status;
    }

    // ============ LINK FIELD ============
    function toggleLinkField() {
        pendingLinkMode = !pendingLinkMode;
        $('link-field-wrap').classList.toggle('hidden', !pendingLinkMode);
        $('btn-link').classList.toggle('active', pendingLinkMode);
        if (pendingLinkMode) $('input-link').focus();
    }

    // ============ ÁUDIO ============
    async function startRecording() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            audioChunks = [];
            mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });

            mediaRecorder.ondataavailable = (e) => audioChunks.push(e.data);
            mediaRecorder.onstop = async () => {
                const blob = new Blob(audioChunks, { type: 'audio/webm' });
                audioChunks = [];
                stream.getTracks().forEach((t) => t.stop());
                await uploadAudio(blob);
            };

            mediaRecorder.start();
            recordingStart = Date.now();
            $('audio-recorder').classList.remove('hidden');
            $('btn-audio').classList.add('active');
            recordingTimer = setInterval(updateAudioTimer, 500);
        } catch (e) {
            showToast('Não foi possível acessar o microfone.', 'error');
        }
    }

    function updateAudioTimer() {
        const elapsed = Math.floor((Date.now() - recordingStart) / 1000);
        const mm = String(Math.floor(elapsed / 60)).padStart(2, '0');
        const ss = String(elapsed % 60).padStart(2, '0');
        $('audio-timer').textContent = `${mm}:${ss}`;
    }

    function stopRecording() {
        if (mediaRecorder && mediaRecorder.state !== 'inactive') {
            mediaRecorder.stop();
        }
        clearInterval(recordingTimer);
        $('audio-recorder').classList.add('hidden');
        $('btn-audio').classList.remove('active');
        $('audio-timer').textContent = '00:00';
    }

    async function uploadAudio(blob) {
        const formData = new FormData();
        formData.append('audio', blob, 'recording.webm');
        showToast('Áudio capturado! Processando...', 'info');
        try {
            const data = await apiFetch('/capture/audio', { method: 'POST', body: formData });
            showToast(`Salvo: ${data.title || 'áudio'}`, 'success');
            loadRecent();
        } catch (e) {
            showToast('Erro ao enviar áudio: ' + e.message, 'error');
        }
    }

    // ============ ARQUIVO / FOTO ============
    async function uploadFile(file) {
        if (!file) return;
        const formData = new FormData();
        formData.append('file', file);
        showToast('Capturado! Processando...', 'info');
        setCaptureLoading(true);
        try {
            const data = await apiFetch('/capture/file', { method: 'POST', body: formData });
            showToast(`Salvo: ${data.title || file.name}`, 'success');
            loadRecent();
        } catch (e) {
            showToast('Erro ao enviar arquivo: ' + e.message, 'error');
        } finally {
            setCaptureLoading(false);
        }
    }

    // ============ DRAG & DROP ============
    function initDragDrop() {
        const box = $('capture-dropzone');
        ['dragenter', 'dragover'].forEach((evt) => {
            box.addEventListener(evt, (e) => {
                e.preventDefault();
                box.classList.add('drag-over');
            });
        });
        ['dragleave', 'drop'].forEach((evt) => {
            box.addEventListener(evt, (e) => {
                e.preventDefault();
                box.classList.remove('drag-over');
            });
        });
        box.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files && files.length) {
                uploadFile(files[0]);
            }
        });
    }

    // ============ CAPTURAR (texto/link) ============
    function setCaptureLoading(loading) {
        const btn = $('btn-capture');
        btn.disabled = loading;
        btn.textContent = loading ? 'CAPTURANDO...' : 'CAPTURAR';
    }

    async function handleCapture() {
        const linkValue = $('input-link').value.trim();
        const textValue = $('capture-textarea').value.trim();

        if (pendingLinkMode && linkValue) {
            await captureLink(linkValue);
            return;
        }

        if (!textValue) {
            showToast('Escreva algo, cole um link ou anexe um arquivo.', 'error');
            return;
        }

        const detected = detectContentType(textValue);
        if (detected.type === 'link') {
            await captureLink(detected.url);
        } else {
            await captureText(textValue);
        }
    }

    async function captureText(text) {
        setCaptureLoading(true);
        showToast('Capturado! Processando...', 'info');
        try {
            const data = await apiFetch('/capture/text', {
                method: 'POST',
                body: JSON.stringify({ text }),
            });
            showToast(`Salvo: ${data.title || 'nota'}`, 'success');
            $('capture-textarea').value = '';
            loadRecent();
        } catch (e) {
            showToast('Erro ao capturar: ' + e.message, 'error');
        } finally {
            setCaptureLoading(false);
        }
    }

    async function captureLink(url) {
        setCaptureLoading(true);
        showToast('Capturado! Processando...', 'info');
        try {
            const data = await apiFetch('/capture/link', {
                method: 'POST',
                body: JSON.stringify({ url }),
            });
            showToast(`Salvo: ${data.title || url}`, 'success');
            $('input-link').value = '';
            $('capture-textarea').value = '';
            if (pendingLinkMode) toggleLinkField();
            loadRecent();
        } catch (e) {
            showToast('Erro ao capturar link: ' + e.message, 'error');
        } finally {
            setCaptureLoading(false);
        }
    }

    // ============ INIT ============
    function init() {
        $('btn-attach').addEventListener('click', () => $('input-file').click());
        $('input-file').addEventListener('change', (e) => {
            if (e.target.files[0]) uploadFile(e.target.files[0]);
            e.target.value = '';
        });

        $('btn-photo').addEventListener('click', () => $('input-photo').click());
        $('input-photo').addEventListener('change', (e) => {
            if (e.target.files[0]) uploadFile(e.target.files[0]);
            e.target.value = '';
        });

        $('btn-link').addEventListener('click', toggleLinkField);

        $('btn-audio').addEventListener('click', () => {
            if (mediaRecorder && mediaRecorder.state === 'recording') {
                stopRecording();
            } else {
                startRecording();
            }
        });
        $('btn-stop-audio').addEventListener('click', stopRecording);

        $('btn-capture').addEventListener('click', handleCapture);

        initDragDrop();
        loadRecent();
    }

    return { init, loadRecent };
})();
