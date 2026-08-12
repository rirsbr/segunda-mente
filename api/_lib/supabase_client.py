"""
Cliente Supabase — conexão via service role key (operações admin/backend).
"""
from functools import lru_cache

from supabase import create_client, Client

from api._lib.config import settings


class SupabaseConfigError(RuntimeError):
    """Levantado quando as variáveis de ambiente do Supabase não estão configuradas."""


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
        raise SupabaseConfigError(
            "SUPABASE_URL e/ou SUPABASE_SERVICE_KEY não configurados. "
            "Defina essas variáveis de ambiente no dashboard da Vercel "
            "(Settings > Environment Variables) e faça um novo deploy."
        )
    return create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_KEY,
    )
