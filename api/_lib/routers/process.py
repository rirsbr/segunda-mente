"""
Rotas de (re)processamento — POST /api/process/{id}, POST /api/process/pending
"""
import logging

from fastapi import APIRouter, HTTPException, Query

from api._lib.supabase_client import get_supabase
from api._lib.processor import process_content

logger = logging.getLogger(__name__)

router = APIRouter()

BATCH_SIZE = 10


@router.post("/process/pending")
async def process_pending(
    offset: int = Query(0, ge=0),
    limit: int = Query(BATCH_SIZE, ge=1, le=BATCH_SIZE),
):
    """
    Processa um LOTE de conteúdos pendentes/com erro por vez — cada item
    envolve extração + classificação + embeddings, o que facilmente
    ultrapassa o timeout de uma função serverless se todos os pendentes
    forem processados numa única request.

    O chamador (frontend) itera: offset=0, depois offset=limit, etc., até
    `done: true`, atualizando uma barra de progresso a cada resposta.
    """
    supabase = get_supabase()

    count_resp = supabase.table("contents").select("id", count="exact").in_("status", ["pending", "error"]).execute()
    total = count_resp.count or 0

    page = supabase.table("contents").select("id").in_("status", ["pending", "error"]) \
        .order("created_at", desc=False) \
        .range(offset, offset + limit - 1).execute()
    ids = [row["id"] for row in (page.data or [])]

    processed, failed = [], []
    for content_id in ids:
        try:
            result = await process_content(content_id)
            processed.append({
                "id": content_id,
                "title": result.get("title"),
                "status": result.get("status"),
            })
        except Exception as exc:
            logger.warning("Falha ao processar %s: %s", content_id, exc)
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


@router.post("/process/{content_id}")
async def process_one(content_id: str):
    supabase = get_supabase()
    existing = supabase.table("contents").select("id,status").eq("id", content_id).limit(1).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Conteúdo não encontrado")

    try:
        result = await process_content(content_id)
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Falha ao processar: {exc}")
