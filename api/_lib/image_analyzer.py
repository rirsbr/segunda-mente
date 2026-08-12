"""
Análise de imagens — OpenAI Vision (via chat completions com input de imagem).
"""
import base64
import logging

from api._lib.config import settings
from api._lib.ai_service import get_openai_client

logger = logging.getLogger(__name__)

VISION_PROMPT = (
    "Descreva esta imagem em português de forma detalhada. Se houver texto "
    "visível (print de tela, documento, placa, etc.), transcreva o texto "
    "também. Seja objetivo e completo, pois esta descrição será usada para "
    "busca e classificação posterior."
)


async def analyze_image(file_bytes: bytes, mime_type: str = "image/jpeg") -> str:
    """Retorna uma descrição textual da imagem usando OpenAI Vision."""
    client = get_openai_client()

    try:
        b64 = base64.b64encode(file_bytes).decode("utf-8")
        data_url = f"data:{mime_type};base64,{b64}"

        response = await client.chat.completions.create(
            model=settings.MODEL_VISION,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": VISION_PROMPT},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                }
            ],
            temperature=0.3,
            max_tokens=800,
        )
        return response.choices[0].message.content or ""
    except Exception as exc:
        logger.exception("Falha ao analisar imagem: %s", exc)
        return ""
