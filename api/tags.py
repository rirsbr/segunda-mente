"""
Rota de tags — GET /api/tags
"""
from fastapi import APIRouter

from api._lib.supabase_client import get_supabase

router = APIRouter()


@router.get("/tags")
async def get_tags():
    supabase = get_supabase()
    resp = supabase.table("tags").select("*").order("name").execute()
    return {"results": resp.data or []}
