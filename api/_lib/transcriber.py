"""
Transcrição de áudio/vídeo — OpenAI Whisper API.
"""
import io
import logging

from api._lib.config import settings
from api._lib.ai_service import get_openai_client

logger = logging.getLogger(__name__)


async def transcribe_audio(file_bytes: bytes, filename: str) -> str:
    """
    Transcreve um arquivo de áudio (ou trilha de áudio de vídeo) usando o
    Whisper API da OpenAI. Retorna o texto transcrito (string vazia em erro).
    """
    client = get_openai_client()

    try:
        buffer = io.BytesIO(file_bytes)
        buffer.name = filename or "audio.webm"

        response = await client.audio.transcriptions.create(
            model=settings.MODEL_WHISPER,
            file=buffer,
            language="pt",
        )
        return response.text or ""
    except Exception as exc:
        logger.exception("Falha ao transcrever áudio %s: %s", filename, exc)
        return ""
