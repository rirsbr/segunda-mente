"""
Pipeline de processamento de conteúdo — extração de texto por tipo,
classificação via LLM, geração de embeddings e persistência no Supabase.

Executado de forma SÍNCRONA dentro da própria request de captura
(ver PROMPT.md, seção "IMPORTANTE sobre Vercel Serverless").
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from api._lib.supabase_client import get_supabase
from api._lib.ai_service import classify_content
from api._lib.embeddings import generate_and_store_embeddings
from api._lib.link_extractor import extract_link_metadata
from api._lib.pdf_extractor import extract_pdf_text
from api._lib.image_analyzer import analyze_image
from api._lib.transcriber import transcribe_audio

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _get_or_create_tag_ids(supabase, tag_names) -> list:
    ids = []
    for raw_name in tag_names or []:
        name = (raw_name or "").strip().lower().replace(" ", "-")
        if not name:
            continue
        try:
            existing = supabase.table("tags").select("id").eq("name", name).limit(1).execute()
            if existing.data:
                ids.append(existing.data[0]["id"])
            else:
                created = supabase.table("tags").insert({"name": name}).execute()
                ids.append(created.data[0]["id"])
        except Exception as exc:
            logger.warning("Falha ao criar/buscar tag '%s': %s", name, exc)
    return ids


async def _save_tags(content_id: str, tag_names) -> None:
    supabase = get_supabase()
    supabase.table("content_tags").delete().eq("content_id", content_id).execute()
    tag_ids = await _get_or_create_tag_ids(supabase, tag_names)
    if not tag_ids:
        return
    rows = [{"content_id": content_id, "tag_id": tid, "confidence": 1.0} for tid in tag_ids]
    supabase.table("content_tags").upsert(rows, on_conflict="content_id,tag_id").execute()


async def _get_or_create_project_ids(supabase, project_names) -> list:
    ids = []
    for raw_name in project_names or []:
        name = (raw_name or "").strip()
        if not name:
            continue
        try:
            existing = supabase.table("projects").select("id").eq("name", name).limit(1).execute()
            if existing.data:
                ids.append(existing.data[0]["id"])
            else:
                created = supabase.table("projects").insert({"name": name}).execute()
                ids.append(created.data[0]["id"])
        except Exception as exc:
            logger.warning("Falha ao criar/buscar projeto '%s': %s", name, exc)
    return ids


async def _save_projects(content_id: str, project_names) -> None:
    supabase = get_supabase()
    supabase.table("content_projects").delete().eq("content_id", content_id).execute()
    project_ids = await _get_or_create_project_ids(supabase, project_names)
    if not project_ids:
        return
    rows = [{"content_id": content_id, "project_id": pid} for pid in project_ids]
    supabase.table("content_projects").upsert(rows, on_conflict="content_id,project_id").execute()


async def _extract_text_for_classification(supabase, content: dict, file_bytes: Optional[bytes],
                                             filename: Optional[str], update_fields: dict) -> str:
    """
    Extrai o texto usado para classificação/embedding conforme o tipo de
    conteúdo. Cada sub-etapa (transcrição, extração de PDF, visão, extração
    de link) é isolada: se UMA falhar (ex: chave da OpenAI inválida, site
    fora do ar), as demais e a classificação seguem normalmente com o que
    já se tem — nunca derruba a captura inteira.
    """
    content_type = content["content_type"]

    if content_type == "text":
        return content.get("original_text") or ""

    if content_type in ("link", "video") and content.get("source_url") and not file_bytes:
        try:
            meta = await extract_link_metadata(content["source_url"])
        except Exception as exc:
            logger.warning("Falha ao extrair metadados do link %s: %s", content["source_url"], exc)
            meta = {}
        if meta.get("platform"):
            update_fields["source_platform"] = meta["platform"]
        if meta.get("thumbnail"):
            update_fields["thumbnail_url"] = meta["thumbnail"]
        if meta.get("duration"):
            update_fields["duration"] = meta["duration"]
        update_fields["extracted_text"] = meta.get("body_text") or meta.get("description") or ""
        if not content.get("title"):
            update_fields["title"] = meta.get("title") or content.get("source_url")
        return "\n".join(filter(None, [
            meta.get("title"), meta.get("description"), meta.get("body_text"),
        ]))

    if content_type in ("audio", "video") and file_bytes:
        try:
            transcription = await transcribe_audio(file_bytes, filename or content.get("file_path") or "audio.webm")
        except Exception as exc:
            logger.warning("Falha ao transcrever %s: %s", content_id_for_log(content), exc)
            transcription = ""
        update_fields["transcription"] = transcription
        return transcription

    if content_type == "pdf" and file_bytes:
        try:
            extracted = extract_pdf_text(file_bytes)
        except Exception as exc:
            logger.warning("Falha ao extrair texto do PDF %s: %s", content_id_for_log(content), exc)
            extracted = ""
        update_fields["extracted_text"] = extracted
        return extracted

    if content_type == "image" and file_bytes:
        try:
            description = await analyze_image(file_bytes, content.get("mime_type") or "image/jpeg")
        except Exception as exc:
            logger.warning("Falha ao analisar imagem %s: %s", content_id_for_log(content), exc)
            description = ""
        update_fields["extracted_text"] = description
        return description

    # Reprocessamento sem arquivo novo: reusar o que já está salvo
    return "\n".join(filter(None, [
        content.get("original_text"),
        content.get("transcription"),
        content.get("extracted_text"),
    ]))


def content_id_for_log(content: dict) -> str:
    return content.get("id") or "?"


async def process_content(
    content_id: str,
    file_bytes: Optional[bytes] = None,
    filename: Optional[str] = None,
) -> dict:
    """
    Processa um conteúdo já criado no banco (status pending/error).

    `file_bytes` é passado apenas no momento da captura original de um
    arquivo (áudio/vídeo/pdf/imagem), quando o arquivo ainda está em
    memória. Em reprocessamentos (POST /api/process/{id}) o arquivo é
    baixado do Supabase Storage a partir de `file_path`, se existir.

    Esta função NUNCA propaga exceção: o conteúdo já foi salvo pelo
    endpoint de captura antes de chegar aqui, então qualquer falha de IA
    (OpenAI fora do ar, chave inválida, site bloqueando scraping, etc.)
    apenas mantém o registro em status 'pending' — o usuário não perde a
    captura e pode reprocessar depois em /api/process/{id}.
    """
    supabase = get_supabase()

    resp = supabase.table("contents").select("*").eq("id", content_id).limit(1).execute()
    if not resp.data:
        raise ValueError(f"Conteúdo {content_id} não encontrado")
    content = resp.data[0]

    try:
        supabase.table("contents").update({"status": "processing"}).eq("id", content_id).execute()
    except Exception as exc:
        logger.warning("Falha ao marcar %s como 'processing' (seguindo mesmo assim): %s", content_id, exc)

    # Se não recebemos o arquivo em memória mas existe file_path, baixar do Storage
    if file_bytes is None and content.get("file_path") and content["content_type"] in (
        "audio", "video", "pdf", "image"
    ):
        try:
            file_bytes = supabase.storage.from_("files").download(content["file_path"])
        except Exception as exc:
            logger.warning("Não foi possível baixar arquivo %s do storage: %s", content["file_path"], exc)

    update_fields: dict = {}

    try:
        text_for_classification = await _extract_text_for_classification(
            supabase, content, file_bytes, filename, update_fields
        )

        # classify_content nunca levanta exceção (tem fallback interno),
        # mas mantemos a rede de segurança por robustez.
        try:
            classification = await classify_content(
                text_for_classification or content.get("title") or content.get("source_url") or ""
            )
        except Exception as exc:
            logger.warning("Classificação falhou para %s, usando fallback: %s", content_id, exc)
            from api._lib.models import ClassificationResult
            fallback_title = (content.get("title") or text_for_classification or "Conteúdo sem título").strip()[:80]
            classification = ClassificationResult(title=fallback_title or "Conteúdo sem título")

        update_fields.setdefault("title", content.get("title"))
        if not update_fields.get("title"):
            update_fields["title"] = classification.title
        update_fields["summary"] = classification.summary
        update_fields["category"] = classification.category
        update_fields["subcategory"] = classification.subcategory
        update_fields["intent"] = classification.intent
        update_fields["status"] = "processed"
        update_fields["error_message"] = None
        update_fields["processed_at"] = _now_iso()

        supabase.table("contents").update(update_fields).eq("id", content_id).execute()

        try:
            await _save_tags(content_id, classification.tags)
        except Exception as exc:
            logger.warning("Falha ao salvar tags de %s: %s", content_id, exc)

        try:
            await _save_projects(content_id, classification.projects)
        except Exception as exc:
            logger.warning("Falha ao salvar projetos de %s: %s", content_id, exc)

        try:
            full_text = "\n".join(filter(None, [
                update_fields.get("title"),
                classification.summary,
                text_for_classification,
            ]))
            await generate_and_store_embeddings(content_id, full_text)
        except Exception as exc:
            logger.warning("Falha ao gerar embeddings de %s: %s", content_id, exc)

        final = supabase.table("contents").select("*").eq("id", content_id).limit(1).execute()
        return final.data[0] if final.data else {**content, **update_fields}

    except Exception as exc:
        # Falha "grande" (ex: Supabase indisponível no meio do processo).
        # O conteúdo bruto já está salvo desde o INSERT original — apenas
        # devolvemos o registro para 'pending' (nunca 'error') para que o
        # usuário veja a captura como sucesso e possa reprocessar depois.
        logger.exception("Erro ao processar conteúdo %s — mantendo como pendente: %s", content_id, exc)
        try:
            supabase.table("contents").update({
                "status": "pending",
                "error_message": str(exc)[:500],
            }).eq("id", content_id).execute()
        except Exception:
            logger.exception("Não foi possível nem gravar o status de pendência de %s", content_id)

        fallback = supabase.table("contents").select("*").eq("id", content_id).limit(1).execute()
        return fallback.data[0] if fallback.data else {**content, "status": "pending"}
