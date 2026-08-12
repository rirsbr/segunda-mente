"""
Extração de metadados de links — yt-dlp (vídeo/áudio) e BeautifulSoup (páginas web).
"""
import logging
import re
from typing import Optional, Dict, Any
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

VIDEO_PLATFORMS = {
    "youtube.com": "youtube",
    "youtu.be": "youtube",
    "vimeo.com": "vimeo",
    "tiktok.com": "tiktok",
    "instagram.com": "instagram",
    "twitter.com": "twitter",
    "x.com": "twitter",
    "facebook.com": "facebook",
}

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


def detect_platform(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
        host = re.sub(r"^www\.", "", host)
        for domain, platform in VIDEO_PLATFORMS.items():
            if domain in host:
                return platform
        return host or "web"
    except Exception:
        return "web"


def _extract_with_ytdlp(url: str) -> Optional[Dict[str, Any]]:
    try:
        import yt_dlp
    except ImportError:
        logger.warning("yt-dlp não disponível")
        return None

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": False,
        "noplaylist": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return None
            return {
                "title": info.get("title"),
                "description": info.get("description"),
                "thumbnail": info.get("thumbnail"),
                "duration": info.get("duration"),
                "uploader": info.get("uploader"),
            }
    except Exception as exc:
        logger.info("yt-dlp não conseguiu extrair %s: %s", url, exc)
        return None


async def _extract_with_bs4(url: str) -> Optional[Dict[str, Any]]:
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
            resp = await client.get(url, headers={"User-Agent": USER_AGENT})
            resp.raise_for_status()
            html = resp.text
    except Exception as exc:
        logger.info("Falha ao baixar HTML de %s: %s", url, exc)
        return None

    soup = BeautifulSoup(html, "html.parser")

    def meta(name: str, prop: bool = False) -> Optional[str]:
        attrs = {"property": name} if prop else {"name": name}
        tag = soup.find("meta", attrs=attrs)
        return tag.get("content") if tag and tag.get("content") else None

    title = (
        meta("og:title", prop=True)
        or (soup.title.string.strip() if soup.title and soup.title.string else None)
    )
    description = meta("og:description", prop=True) or meta("description")
    image = meta("og:image", prop=True)

    # Texto principal da página (parágrafos), limitado
    paragraphs = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
    body_text = "\n".join(p for p in paragraphs if p)[:8000]

    return {
        "title": title,
        "description": description,
        "thumbnail": image,
        "body_text": body_text,
    }


async def extract_link_metadata(url: str) -> Dict[str, Any]:
    """
    Extrai metadados de uma URL. Tenta yt-dlp primeiro (plataformas de vídeo
    conhecidas), depois cai para BeautifulSoup (páginas web genéricas).
    """
    platform = detect_platform(url)
    result: Dict[str, Any] = {
        "platform": platform,
        "title": None,
        "description": None,
        "thumbnail": None,
        "duration": None,
        "body_text": "",
        "content_type": "video" if platform in {"youtube", "vimeo", "tiktok"} else "link",
    }

    if platform in {"youtube", "vimeo", "tiktok", "twitter", "instagram", "facebook"}:
        info = _extract_with_ytdlp(url)
        if info:
            result.update({
                "title": info.get("title"),
                "description": info.get("description"),
                "thumbnail": info.get("thumbnail"),
                "duration": info.get("duration"),
            })
            result["body_text"] = info.get("description") or ""
            return result

    bs_info = await _extract_with_bs4(url)
    if bs_info:
        result["title"] = result["title"] or bs_info.get("title")
        result["description"] = result["description"] or bs_info.get("description")
        result["thumbnail"] = result["thumbnail"] or bs_info.get("thumbnail")
        result["body_text"] = bs_info.get("body_text", "")
        result["content_type"] = "link"

    if not result["title"]:
        result["title"] = url

    return result
