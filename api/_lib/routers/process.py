"""
Rotas de (re)processamento — POST /api/process/{id}, POST /api/process/pending
"""
import logging

from fastapi import APIRouter, HTTPException

from api._lib.supabase_client import get_supabase
from api._lib.processor import process_content

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/process/pending")
async def process_pending():
    supabase = get_supabase()
    resp = supabase.table("contents").select("id").in_("status", ["pending", "error"]).execute()
    ids = [row["id"] for row in (resp.data or [])]

    processed, failed = [], []
    for content_id in ids:
        try:
            await process_content(content_id)
            processed.append(content_id)
        except Exception as exc:
            logger.warning("Falha ao reprocessar %s: %s", content_id, exc)
            failed.append(content_id)

    return {"processed": processed, "failed": failed, "total": len(ids)}


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
