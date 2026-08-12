"""
Rotas de captura — POST /api/capture/text, /link, /file, /audio
"""
import logging
import mimetypes
import os
import uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from api._lib.config import settings
from api._lib.models import CaptureLinkRequest, CaptureResponse, CaptureTextRequest
from api._lib.supabase_client import get_supabase
from api._lib.link_extractor import detect_platform
from api._lib.processor import process_content

logger = logging.getLogger(__name__)

router = APIRouter()

VIDEO_PLATFORMS = {"youtube", "vimeo", "tiktok"}


def _ext_to_content_type(filename: str) -> str:
    ext = os.path.splitext(filename or "")[1].lower()
    if ext in settings.AUDIO_EXTENSIONS:
        return "audio"
    if ext in settings.VIDEO_EXTENSIONS:
        return "video"
    if ext in settings.IMAGE_EXTENSIONS:
        return "image"
    if ext in settings.PDF_EXTENSIONS:
        return "pdf"
    if ext in settings.DOC_EXTENSIONS:
        return "text"
    return "text"


def _insert_content(supabase, data: dict) -> str:
    """
    Insere o registro inicial em `contents`. Qualquer falha aqui (Supabase
    fora do ar, credenciais erradas, coluna/constraint inválida) vira um
    HTTPException com mensagem legível — nunca um 500 opaco silencioso.
    """
    try:
        insert = supabase.table("contents").insert(data).execute()
    except Exception as exc:
        logger.exception("Falha ao inserir conteúdo no Supabase: %s", exc)
        raise HTTPException(status_code=502, detail=f"Falha ao salvar no banco de dados: {exc}")

    if not insert.data:
        raise HTTPException(status_code=502, detail="Falha ao criar registro: resposta vazia do Supabase")

    return insert.data[0]["id"]


async def _run_pipeline(content_id: str, file_bytes: bytes = None, filename: str = None) -> CaptureResponse:
    """
    Roda o pipeline de IA (extração + classificação + embeddings) para o
    conteúdo já salvo. `process_content` nunca propaga exceção — na pior
    hipótese o conteúdo fica com status 'pending' e error_message
    preenchido, mas a captura em si é sempre considerada bem-sucedida
    (o dado do usuário já está salvo desde o INSERT).
    """
    try:
        result = await process_content(content_id, file_bytes=file_bytes, filename=filename)
        status = result.get("status", "pending")
        message = (
            "Capturado e processado com sucesso."
            if status == "processed"
            else "Capturado! O enriquecimento com IA ainda está pendente — você pode reprocessar depois."
        )
        return CaptureResponse(
            id=content_id,
            status=status,
            title=result.get("title"),
            message=message,
        )
    except Exception as exc:
        # Rede de segurança final: mesmo que algo totalmente inesperado
        # aconteça aqui, o registro já existe no banco (status 'pending'),
        # então ainda respondemos 200 em vez de derrubar a captura.
        logger.exception("Falha inesperada no pipeline de captura %s: %s", content_id, exc)
        return CaptureResponse(
            id=content_id,
            status="pending",
            title=None,
            message="Capturado! Houve um problema ao processar com IA — você pode reprocessar depois.",
        )


@router.post("/capture/text", response_model=CaptureResponse)
async def capture_text(payload: CaptureTextRequest):
    text = (payload.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Texto vazio")

    supabase = get_supabase()
    content_id = _insert_content(supabase, {
        "content_type": "text",
        "original_text": text,
        "status": "pending",
    })

    return await _run_pipeline(content_id)


@router.post("/capture/link", response_model=CaptureResponse)
async def capture_link(payload: CaptureLinkRequest):
    url = (payload.url or "").strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        raise HTTPException(status_code=400, detail="URL inválida")

    platform = detect_platform(url)
    content_type = "video" if platform in VIDEO_PLATFORMS else "link"

    supabase = get_supabase()
    content_id = _insert_content(supabase, {
        "content_type": content_type,
        "source_url": url,
        "source_platform": platform,
        "original_text": payload.note or None,
        "status": "pending",
    })

    return await _run_pipeline(content_id)


@router.post("/capture/file", response_model=CaptureResponse)
async def capture_file(file: UploadFile = File(...), note: str = Form(None)):
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Arquivo vazio")

    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > settings.MAX_FILE_SIZE_MB:
        raise HTTPException(status_code=413, detail=f"Arquivo maior que {settings.MAX_FILE_SIZE_MB}MB")

    content_type = _ext_to_content_type(file.filename)
    mime_type = file.content_type or mimetypes.guess_type(file.filename or "")[0] or "application/octet-stream"

    supabase = get_supabase()
    storage_path = f"{uuid.uuid4()}/{file.filename}"

    try:
        supabase.storage.from_(settings.STORAGE_BUCKET).upload(
            storage_path, file_bytes, {"content-type": mime_type}
        )
    except Exception as exc:
        logger.exception("Falha no upload para Storage: %s", exc)
        raise HTTPException(status_code=502, detail=f"Falha ao enviar arquivo para o armazenamento: {exc}")

    insert_data = {
        "content_type": content_type,
        "original_text": note or None,
        "file_path": storage_path,
        "file_size": len(file_bytes),
        "mime_type": mime_type,
        "status": "pending",
    }

    if content_type == "text":
        # Documentos .txt/.md: usar o próprio conteúdo como texto original
        try:
            insert_data["original_text"] = file_bytes.decode("utf-8", errors="ignore")
        except Exception:
            pass

    content_id = _insert_content(supabase, insert_data)

    return await _run_pipeline(content_id, file_bytes=file_bytes, filename=file.filename)


@router.post("/capture/audio", response_model=CaptureResponse)
async def capture_audio(audio: UploadFile = File(...)):
    file_bytes = await audio.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Áudio vazio")

    mime_type = audio.content_type or "audio/webm"
    filename = audio.filename or "recording.webm"

    supabase = get_supabase()
    storage_path = f"{uuid.uuid4()}/{filename}"

    try:
        supabase.storage.from_(settings.STORAGE_BUCKET).upload(
            storage_path, file_bytes, {"content-type": mime_type}
        )
    except Exception as exc:
        logger.exception("Falha no upload de áudio: %s", exc)
        raise HTTPException(status_code=502, detail=f"Falha ao enviar áudio para o armazenamento: {exc}")

    content_id = _insert_content(supabase, {
        "content_type": "audio",
        "file_path": storage_path,
        "file_size": len(file_bytes),
        "mime_type": mime_type,
        "status": "pending",
    })

    return await _run_pipeline(content_id, file_bytes=file_bytes, filename=filename)
