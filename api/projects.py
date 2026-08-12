"""
Rotas de projetos — GET/POST /api/projects
"""
from fastapi import APIRouter, HTTPException

from api._lib.models import ProjectCreateRequest
from api._lib.supabase_client import get_supabase

router = APIRouter()


@router.get("/projects")
async def get_projects():
    supabase = get_supabase()
    resp = supabase.table("projects").select("*").order("name").execute()
    return {"results": resp.data or []}


@router.post("/projects")
async def create_project(payload: ProjectCreateRequest):
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Nome do projeto é obrigatório")

    supabase = get_supabase()
    existing = supabase.table("projects").select("id").eq("name", name).limit(1).execute()
    if existing.data:
        raise HTTPException(status_code=409, detail="Já existe um projeto com esse nome")

    resp = supabase.table("projects").insert({
        "name": name,
        "description": payload.description,
    }).execute()
    return resp.data[0] if resp.data else {"name": name, "description": payload.description}
