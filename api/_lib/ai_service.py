"""
Serviço de IA — classificação de conteúdo e chat (OpenAI GPT-4o-mini).
"""
import json
import logging
from typing import List, Dict, Any

from openai import AsyncOpenAI

from api._lib.config import settings, CLASSIFICATION_PROMPT, ASK_SYSTEM_PROMPT
from api._lib.models import ClassificationResult

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None


def get_openai_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


def _strip_markdown_json(raw: str) -> str:
    """Remove cercas ```json ... ``` que o modelo às vezes retorna."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.endswith("```"):
            text = text[: -3]
        if text.lstrip().lower().startswith("json"):
            text = text.lstrip()[4:]
    return text.strip()


async def classify_content(content_text: str) -> ClassificationResult:
    """
    Classifica um conteúdo textual usando GPT-4o-mini.
    Retorna título, resumo, categoria, subcategoria, tags, intenção, projetos.
    """
    client = get_openai_client()

    # Limitar tamanho do conteúdo enviado ao LLM (evitar custo/limite de tokens)
    truncated = content_text[:12000] if content_text else ""

    prompt = CLASSIFICATION_PROMPT.format(content=truncated)

    try:
        response = await client.chat.completions.create(
            model=settings.MODEL_CLASSIFY,
            messages=[
                {"role": "system", "content": "Você retorna apenas JSON válido, sem formatação markdown."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or "{}"
        raw = _strip_markdown_json(raw)
        data = json.loads(raw)
        return ClassificationResult(**data)
    except Exception as exc:
        logger.exception("Falha ao classificar conteúdo: %s", exc)
        # Fallback seguro — não deve travar o pipeline de captura
        fallback_title = (content_text or "Conteúdo sem título").strip()[:80] or "Conteúdo sem título"
        return ClassificationResult(
            title=fallback_title,
            summary="",
            category="Outros",
            subcategory="",
            tags=[],
            intent="lembrar",
            projects=[],
            language="pt",
        )


async def openai_chat(model: str, messages: List[Dict[str, Any]], temperature: float = 0.5) -> str:
    """Chamada genérica de chat ao OpenAI, retorna apenas o texto da resposta."""
    client = get_openai_client()
    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )
    return response.choices[0].message.content or ""


async def ask_llm(question: str, context: str, results_count: int) -> str:
    """Pergunta ao LLM usando o contexto de conteúdos encontrados na base."""
    messages = [
        {"role": "system", "content": ASK_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"""Pergunta: {question}

Conteúdos encontrados na base ({results_count} resultados):
{context}

Responda a pergunta usando os conteúdos acima.""",
        },
    ]
    return await openai_chat(settings.MODEL_CHAT, messages)
