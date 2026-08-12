"""
Cliente Supabase — conexão via service role key (operações admin/backend).
"""
from functools import lru_cache
from supabase import create_client, Client
from api._lib.config import settings


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_KEY,
    )
