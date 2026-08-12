"""
Rotas de busca — GET /api/search (híbrida com filtros) e POST /api/ask (chat).
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from api._lib.models import AskRequest
from api._lib.search import hybrid_search
from api._lib.ai_service import ask_llm

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/search")
async def search(
    q: str = Query(..., min_length=1),
    type: Optional[str] = None,
    category: Optional[str] = None,
    from_: Optional[str] = Query(None, alias="from"),
    to: Optional[str] = None,
    reviewed: Optional[bool] = None,
    limit: int = Query(20, le=100),
    offset: int = 0,
):
    filters = {
        "type": type,
        "category": category,
        "from": from_,
        "to": to,
        "reviewed": reviewed,
    }
    results = await hybrid_search(q, filters=filters, limit=limit + offset)
    page = results[offset: offset + limit]
    return {"results": page, "total": len(results)}


@router.post("/ask")
async def ask(payload: AskRequest):
    question = (payload.question or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="Pergunta vazia")

    results = await hybrid_search(question, filters={}, limit=10)

    context_parts = []
    for r in results[:8]:
        context_parts.append(
            f"[{(r.get('content_type') or '').upper()}] {r.get('title') or 'Sem título'}\n"
            f"Categoria: {r.get('category') or 'N/A'}\n"
            f"Resumo: {r.get('summary') or 'N/A'}\n"
            f"Data: {r.get('created_at') or 'N/A'}\n"
        )
    context = "\n---\n".join(context_parts)

    if context:
        answer = await ask_llm(question, context, len(results))
    else:
        answer = "Não encontrei nenhum conteúdo relevante na sua base para essa pergunta."

    return {
        "answer": answer,
        "contents": results[:5],
        "total_found": len(results),
    }
