"""
Geração de embeddings — OpenAI text-embedding-3-small.
"""
import logging
from typing import List

from api._lib.config import settings
from api._lib.ai_service import get_openai_client
from api._lib.supabase_client import get_supabase

logger = logging.getLogger(__name__)

# Tamanho aproximado de cada chunk (em caracteres) para textos longos
CHUNK_SIZE = 3000
CHUNK_OVERLAP = 200


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Quebra texto longo em pedaços menores para embeddings mais precisos."""
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
        if start >= len(text):
            break
    return chunks


async def get_embedding(text: str) -> List[float]:
    """Gera embedding de um texto único via OpenAI."""
    client = get_openai_client()
    text = (text or "").strip()[:8000]
    if not text:
        text = " "
    response = await client.embeddings.create(
        model=settings.MODEL_EMBEDDING,
        input=text,
    )
    return response.data[0].embedding


async def generate_and_store_embeddings(content_id: str, full_text: str) -> int:
    """
    Gera embeddings (por chunk, se necessário) para o texto completo de um
    conteúdo e salva em content_embeddings. Retorna a quantidade de chunks salvos.
    """
    supabase = get_supabase()
    chunks = chunk_text(full_text)

    if not chunks:
        return 0

    # Limpa embeddings antigos deste conteúdo (caso seja reprocessamento)
    supabase.table("content_embeddings").delete().eq("content_id", content_id).execute()

    saved = 0
    for idx, chunk in enumerate(chunks):
        try:
            vector = await get_embedding(chunk)
            supabase.table("content_embeddings").insert({
                "content_id": content_id,
                "embedding": vector,
                "chunk_text": chunk,
                "chunk_index": idx,
            }).execute()
            saved += 1
        except Exception as exc:
            logger.exception("Falha ao gerar embedding do chunk %s de %s: %s", idx, content_id, exc)

    return saved
