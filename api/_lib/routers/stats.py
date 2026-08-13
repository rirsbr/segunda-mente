"""
Rota de estatísticas — GET /api/stats
"""
from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter

from api._lib.supabase_client import get_supabase

router = APIRouter()


@router.get("/stats")
async def get_stats():
    supabase = get_supabase()

    contents_resp = supabase.table("contents").select(
        "id, content_type, category, status, is_reviewed, created_at"
    ).execute()
    contents = contents_resp.data or []

    total = len(contents)
    by_type = Counter(c["content_type"] for c in contents if c.get("content_type"))
    by_category = Counter(c["category"] for c in contents if c.get("category"))
    pending = sum(1 for c in contents if c.get("status") in ("pending", "processing"))
    unreviewed = sum(1 for c in contents if not c.get("is_reviewed"))

    seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    recent_7d = sum(1 for c in contents if c.get("created_at") and c["created_at"] >= seven_days_ago)

    tags_resp = supabase.table("content_tags").select("tags(name)").execute()
    tag_counter = Counter()
    for row in (tags_resp.data or []):
        tag = row.get("tags") or {}
        name = tag.get("name") if isinstance(tag, dict) else None
        if name:
            tag_counter[name] += 1

    top_tags = [{"name": name, "count": count} for name, count in tag_counter.most_common(20)]

    return {
        "total": total,
        "by_type": dict(by_type),
        "by_category": dict(by_category),
        "pending": pending,
        "unreviewed": unreviewed,
        "recent_7d": recent_7d,
        "top_tags": top_tags,
    }
