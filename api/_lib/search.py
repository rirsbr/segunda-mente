"""
Busca híbrida — combina busca vetorial (pgvector) e full-text (PostgreSQL)
via Reciprocal Rank Fusion (RRF).
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from api._lib.supabase_client import get_supabase
from api._lib.embeddings import get_embedding

logger = logging.getLogger(__name__)


def reciprocal_rank_fusion(vector_ids, fts_ids, k: int = 60):
    """Combina dois rankings usando RRF."""
    scores: Dict[str, float] = {}
    for rank, (cid, _) in enumerate(vector_ids):
        scores[cid] = scores.get(cid, 0) + 1 / (k + rank + 1)
    for rank, (cid, _) in enumerate(fts_ids):
        scores[cid] = scores.get(cid, 0) + 1 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


def apply_filters(contents: List[dict], filters: Dict[str, Any]) -> List[dict]:
    """Aplica filtros de tipo, categoria, data e revisão em memória."""
    result = contents

    content_type = filters.get("type")
    if content_type:
        result = [c for c in result if c.get("content_type") == content_type]

    category = filters.get("category")
    if category:
        result = [c for c in result if c.get("category") == category]

    reviewed = filters.get("reviewed")
    if reviewed is not None:
        result = [c for c in result if bool(c.get("is_reviewed")) == bool(reviewed)]

    date_from = filters.get("from")
    if date_from:
        result = [c for c in result if c.get("created_at") and c["created_at"] >= date_from]

    date_to = filters.get("to")
    if date_to:
        result = [c for c in result if c.get("created_at") and c["created_at"] <= date_to]

    return result


async def _attach_tags(contents: List[dict]) -> List[dict]:
    """Anexa a lista de nomes de tags a cada conteúdo."""
    if not contents:
        return contents
    supabase = get_supabase()
    ids = [c["id"] for c in contents]
    try:
        rows = supabase.table("content_tags").select("content_id, tags(name)").in_("content_id", ids).execute()
        by_content: Dict[str, List[str]] = {}
        for row in rows.data or []:
            tag = row.get("tags") or {}
            name = tag.get("name") if isinstance(tag, dict) else None
            if name:
                by_content.setdefault(row["content_id"], []).append(name)
        for c in contents:
            c["tags"] = by_content.get(c["id"], [])
    except Exception as exc:
        logger.warning("Falha ao anexar tags: %s", exc)
        for c in contents:
            c.setdefault("tags", [])
    return contents


async def hybrid_search(query: str, filters: Optional[Dict[str, Any]] = None, limit: int = 20) -> List[dict]:
    """
    Busca híbrida: vetorial (pgvector) + full-text (PostgreSQL), combinadas
    via Reciprocal Rank Fusion, com filtros aplicados por último.
    """
    filters = filters or {}
    supabase = get_supabase()

    query_embedding = await get_embedding(query)

    vector_ids: List[tuple] = []
    try:
        vector_results = supabase.rpc("match_embeddings", {
            "query_embedding": query_embedding,
            "match_threshold": 0.3,
            "match_count": limit,
        }).execute()
        vector_ids = [(r["content_id"], r["similarity"]) for r in (vector_results.data or [])]
    except Exception as exc:
        logger.warning("Busca vetorial falhou: %s", exc)

    fts_ids: List[tuple] = []
    try:
        fts_results = supabase.rpc("search_contents_fts", {
            "search_query": query,
            "max_results": limit,
        }).execute()
        fts_ids = [(r["id"], r["rank"]) for r in (fts_results.data or [])]
    except Exception as exc:
        logger.warning("Busca full-text falhou: %s", exc)

    combined = reciprocal_rank_fusion(vector_ids, fts_ids, k=60)
    if not combined:
        return []

    scores = dict(combined)
    max_score = max(scores.values()) if scores else 0

    content_ids = [c[0] for c in combined[: max(limit * 3, limit)]]
    contents_resp = supabase.table("contents").select("*").in_("id", content_ids).execute()
    contents = contents_resp.data or []

    filtered = apply_filters(contents, filters)

    id_order = {cid: i for i, (cid, _) in enumerate(combined)}
    filtered.sort(key=lambda c: id_order.get(c["id"], 999999))

    filtered = filtered[:limit]

    # Score de relevância (0-100), relativo ao melhor resultado desta busca —
    # usado no frontend para a barra colorida e o badge "% relevante".
    for c in filtered:
        raw = scores.get(c["id"], 0)
        c["relevance_score"] = round((raw / max_score) * 100) if max_score else 0

    filtered = await _attach_tags(filtered)
    return filtered


async def list_contents(filters: Optional[Dict[str, Any]] = None, sort: str = "created_at",
                         order: str = "desc", limit: int = 20, offset: int = 0):
    """Listagem simples (sem busca semântica) para a tela de Biblioteca."""
    filters = filters or {}
    supabase = get_supabase()

    q = supabase.table("contents").select("*", count="exact")

    if filters.get("type"):
        q = q.eq("content_type", filters["type"])
    if filters.get("category"):
        q = q.eq("category", filters["category"])
    if filters.get("status"):
        q = q.eq("status", filters["status"])
    if filters.get("reviewed") is not None:
        q = q.eq("is_reviewed", filters["reviewed"])
    if filters.get("from"):
        q = q.gte("created_at", filters["from"])
    if filters.get("to"):
        q = q.lte("created_at", filters["to"])

    tag_name = filters.get("tag")
    if tag_name:
        tag_resp = supabase.table("tags").select("id").eq("name", tag_name).limit(1).execute()
        if not tag_resp.data:
            return [], 0
        tag_id = tag_resp.data[0]["id"]
        ct_resp = supabase.table("content_tags").select("content_id").eq("tag_id", tag_id).execute()
        content_ids = [row["content_id"] for row in (ct_resp.data or [])]
        if not content_ids:
            return [], 0
        q = q.in_("id", content_ids)

    desc = order != "asc"
    q = q.order(sort, desc=desc)
    q = q.range(offset, offset + limit - 1)

    resp = q.execute()
    contents = resp.data or []
    contents = await _attach_tags(contents)
    return contents, (resp.count or 0)
