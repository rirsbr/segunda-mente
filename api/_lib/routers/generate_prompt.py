"""
Rota de geração de prompt executável — POST /api/generate-prompt.

Pega um conteúdo já salvo (título, resumo, transcrição/texto original, tags)
e usa o LLM para transformá-lo num prompt pronto para colar em outra IA
(Claude, ChatGPT) e executar/implementar o que foi descrito.
"""
import logging

from fastapi import APIRouter, HTTPException

from api._lib.ai_service import generate_execution_prompt
from api._lib.models import GeneratePromptRequest
from api._lib.supabase_client import get_supabase

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/generate-prompt")
async def generate_prompt(payload: GeneratePromptRequest):
    supabase = get_supabase()
    resp = supabase.table("contents").select(
        "title, summary, original_text, transcription, extracted_text, category, subcategory"
    ).eq("id", payload.content_id).limit(1).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Conteúdo não encontrado")

    content = resp.data[0]

    tags_resp = supabase.table("content_tags").select("tags(name)").eq(
        "content_id", payload.content_id
    ).execute()
    tags = [row["tags"]["name"] for row in (tags_resp.data or []) if row.get("tags")]

    body_text = content.get("transcription") or content.get("original_text") or content.get("extracted_text") or ""
    category_line = " > ".join(filter(None, [content.get("category"), content.get("subcategory")]))

    context = f"""Título: {content.get('title') or 'Sem título'}
Categoria: {category_line or 'N/A'}
Tags: {', '.join(tags) or 'N/A'}
Resumo: {content.get('summary') or 'N/A'}

Conteúdo:
{body_text[:8000]}"""

    try:
        prompt = await generate_execution_prompt(context)
    except Exception as exc:
        logger.exception("Falha ao gerar prompt para %s: %s", payload.content_id, exc)
        raise HTTPException(status_code=500, detail=f"Falha ao gerar prompt: {exc}")

    return {"prompt": prompt.strip()}
