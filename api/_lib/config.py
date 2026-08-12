"""
Configurações da aplicação — variáveis de ambiente.
"""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class Settings:
    OPENAI_API_KEY: str = os.environ.get("OPENAI_API_KEY", "")
    SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.environ.get("SUPABASE_KEY", "")
    SUPABASE_SERVICE_KEY: str = os.environ.get("SUPABASE_SERVICE_KEY", "")

    STORAGE_BUCKET: str = "files"

    # Modelos OpenAI
    MODEL_CLASSIFY: str = "gpt-4o-mini"
    MODEL_CHAT: str = "gpt-4o-mini"
    MODEL_EMBEDDING: str = "text-embedding-3-small"
    MODEL_WHISPER: str = "whisper-1"
    MODEL_VISION: str = "gpt-4o-mini"

    EMBEDDING_DIMENSIONS: int = 1536

    # Limites de upload
    MAX_FILE_SIZE_MB: int = 100

    # Extensões aceitas por tipo
    AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a", ".webm"}
    VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".mkv"}
    IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
    PDF_EXTENSIONS = {".pdf"}
    DOC_EXTENSIONS = {".txt", ".md"}


settings = Settings()

# ===================================
# CATEGORIAS PRÉ-DEFINIDAS
# ===================================
CATEGORIES = {
    "Inteligência Artificial": [
        "Agentes", "Geração de Texto", "Geração de Imagem",
        "Geração de Vídeo", "Automação com IA", "LLMs",
        "RAG", "MCP", "Embeddings", "Fine-tuning", "Prompts"
    ],
    "Programação": [
        "Python", "JavaScript", "HTML/CSS", "Banco de Dados",
        "APIs", "DevOps", "Git", "Ferramentas"
    ],
    "Negócios": [
        "Ideias de Negócio", "Marketing Digital", "E-commerce",
        "Afiliados", "Produtos Digitais", "Monetização"
    ],
    "Trabalho": [
        "Petrobras", "P-43", "Produção", "Procedimentos",
        "Segurança", "Melhorias", "Instrumentação"
    ],
    "Pessoal": [
        "Ideias", "Estudos", "Compras", "Viagens",
        "Saúde", "Finanças", "Casa"
    ],
    "Outros": []
}

KNOWN_PROJECTS = ["Segunda Mente", "LIBRA", "APLAT", "Media Company"]

CLASSIFICATION_PROMPT = """Você é um assistente de organização pessoal. Analise o conteúdo abaixo e retorne APENAS um JSON válido (sem markdown, sem explicações):

{{
    "title": "Título claro e descritivo em português (max 100 chars)",
    "summary": "Resumo conciso em 2-3 frases em português",
    "category": "Uma das: Inteligência Artificial, Programação, Negócios, Trabalho, Pessoal, Outros",
    "subcategory": "Subcategoria específica",
    "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
    "intent": "Uma de: estudar, assistir, lembrar, ideia, referencia, executar",
    "projects": ["nomes de projetos relacionados"],
    "language": "pt ou en"
}}

Projetos conhecidos: Segunda Mente, LIBRA, APLAT, Media Company.
Interesses do usuário: IA (agentes, geração de conteúdo, automação), programação (Python, web), negócios digitais, automação industrial.

REGRAS:
- Tags em minúsculas, sem acento, sem espaços (use hifens)
- Se conteúdo em inglês, título e resumo em português
- Se não conseguir classificar, use category "Outros"
- Sempre retorne JSON válido

Conteúdo:
---
{content}
---"""

ASK_SYSTEM_PROMPT = """Você é a Segunda Mente — o assistente pessoal de conhecimento do Rodrigo.
Você tem acesso à base de conteúdos que ele salvou ao longo do tempo.
Responda de forma direta, útil e em português.
Referencie os conteúdos encontrados pelo título.
Se não encontrar nada relevante, diga isso claramente.
Não invente conteúdos que não estão na base."""
