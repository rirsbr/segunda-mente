"""
Extração de texto de PDFs — PyMuPDF (fitz).
"""
import logging

logger = logging.getLogger(__name__)


def extract_pdf_text(file_bytes: bytes) -> str:
    """Extrai todo o texto de um PDF a partir dos bytes do arquivo."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.warning("PyMuPDF (fitz) não disponível")
        return ""

    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        parts = []
        for page in doc:
            parts.append(page.get_text())
        doc.close()
        return "\n\n".join(parts).strip()
    except Exception as exc:
        logger.exception("Falha ao extrair texto do PDF: %s", exc)
        return ""
