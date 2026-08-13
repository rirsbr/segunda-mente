"""
Rotas de reclassificação — reaplicam o prompt de classificação atual em
conteúdos já processados, sem re-extrair texto nem regerar embeddings.

Usado depois de melhorar o CLASSIFICATION_PROMPT (api/_lib/config.py) para
"corrigir" categorias/tags ruins que já estão salvas na base, sem pagar de
novo o custo de Whisper/PDF/Vision/scraping.
"""
import logging

from fastapi import APIRouter, HTTPException, Query

from api._lib.supabase_client import get_supabase
from api._lib.processor import reclassify_content

logger = logging.getLogger(__name__)

router = APIRouter()

BATCH_SIZE = 10


@router.post("/reclassify/all")
async def reclassify_all(
    offset: int = Query(0, ge=0),
    limit: int = Query(BATCH_SIZE, ge=1, le=BATCH_SIZE),
):
    """
    Reclassifica um LOTE de conteúdos já processados por vez (a função
    serverless tem timeout — reclassificar tudo de uma vez estouraria).

    O chamador (frontend) itera: chama com offset=0, depois offset=limit,
    offset=2*limit, etc., até `done: true`. Cada chamada retorna progresso
    parcial (processed/failed/offset/total/done) para atualizar uma barra
    de progresso na interface.
    """
    supabase = get_supabase()

    count_resp = supabase.table("contents").select("id", count="exact").eq("status", "processed").execute()
    total = count_resp.count or 0

    page = supabase.table("contents").select("id").eq("status", "processed") \
        .order("created_at", desc=False) \
        .range(offset, offset + limit - 1).execute()
    ids = [row["id"] for row in (page.data or [])]

    processed, failed = [], []
    for content_id in ids:
        try:
            result = await reclassify_content(content_id)
            processed.append({
                "id": content_id,
                "title": result.get("title"),
                "category": result.get("category"),
            })
        except Exception as exc:
            logger.warning("Falha ao reclassificar %s: %s", content_id, exc)
            failed.append(content_id)

    next_offset = offset + len(ids)
    return {
        "processed": processed,
        "failed": failed,
        "offset": offset,
        "next_offset": next_offset,
        "limit": limit,
        "total": total,
        "done": next_offset >= total,
    }


@router.post("/reclassify/{content_id}")
async def reclassify_one(content_id: str):
    supabase = get_supabase()
    existing = supabase.table("contents").select("id").eq("id", content_id).limit(1).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Conteúdo não encontrado")

    try:
        result = await reclassify_content(content_id)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Falha ao reclassificar: {exc}")
