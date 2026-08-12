"""
Rotas de biblioteca — GET/PATCH/DELETE /api/contents
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from api._lib.config import settings
from api._lib.models import ContentUpdateRequest
from api._lib.supabase_client import get_supabase
from api._lib.search import list_contents, _attach_tags

logger = logging.getLogger(__name__)

router = APIRouter()


async def _attach_projects(content: dict) -> dict:
    supabase = get_supabase()
    try:
        rows = supabase.table("content_projects").select("projects(name)").eq(
            "content_id", content["id"]
        ).execute()
        content["projects"] = [
            r["projects"]["name"] for r in (rows.data or []) if r.get("projects")
        ]
    except Exception as exc:
        logger.warning("Falha ao anexar projetos: %s", exc)
        content["projects"] = []
    return content


@router.get("/contents")
async def get_contents(
    type: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    reviewed: Optional[bool] = None,
    sort: str = "created_at",
    order: str = "desc",
    limit: int = Query(20, le=100),
    offset: int = 0,
):
    filters = {"type": type, "category": category, "status": status, "reviewed": reviewed}
    contents, total = await list_contents(filters=filters, sort=sort, order=order, limit=limit, offset=offset)
    return {"results": contents, "total": total}


@router.get("/contents/{content_id}")
async def get_content(content_id: str):
    supabase = get_supabase()
    resp = supabase.table("contents").select("*").eq("id", content_id).limit(1).execute()
    if not resp.data:
        raise HTTPException(status_code=404, detail="Conteúdo não encontrado")

    content = resp.data[0]
    content = (await _attach_tags([content]))[0]
    content = await _attach_projects(content)
    return content


@router.patch("/contents/{content_id}")
async def update_content(content_id: str, payload: ContentUpdateRequest):
    supabase = get_supabase()
    existing = supabase.table("contents").select("id").eq("id", content_id).limit(1).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Conteúdo não encontrado")

    update_data = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="Nenhum campo para atualizar")

    resp = supabase.table("contents").update(update_data).eq("id", content_id).execute()
    return resp.data[0] if resp.data else {"id": content_id, **update_data}


@router.delete("/contents/{content_id}")
async def delete_content(content_id: str):
    supabase = get_supabase()
    existing = supabase.table("contents").select("file_path").eq("id", content_id).limit(1).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Conteúdo não encontrado")

    file_path = existing.data[0].get("file_path")
    if file_path:
        try:
            supabase.storage.from_(settings.STORAGE_BUCKET).remove([file_path])
        except Exception as exc:
            logger.warning("Falha ao remover arquivo do storage %s: %s", file_path, exc)

    supabase.table("contents").delete().eq("id", content_id).execute()
    return {"deleted": True, "id": content_id}
