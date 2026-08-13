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
# CATEGORIAS — específicas por assunto, nunca por plataforma.
# Cada uma já é o valor final salvo em `contents.category`.
# ===================================
CATEGORIES = [
    "IA - Geração de Vídeo",
    "IA - Geração de Imagem",
    "IA - Geração de Texto",
    "IA - Agentes e Automação",
    "IA - Ferramentas",
    "Marketing Digital",
    "Negócios e Empreendedorismo",
    "Programação",
    "Trabalho - Petrobras",
    "Casa e Pessoal",
    "Entretenimento",
    "Outro",
]

# Categorias que compartilham o mesmo "grupo" no filtro da Biblioteca
# (ex: clicar em "IA" mostra estas 5 como subfiltros). Usado só pelo frontend,
# mas mantido aqui como fonte única da verdade.
CATEGORY_GROUPS = {
    "IA": [
        "IA - Geração de Vídeo",
        "IA - Geração de Imagem",
        "IA - Geração de Texto",
        "IA - Agentes e Automação",
        "IA - Ferramentas",
    ],
    "Marketing Digital": ["Marketing Digital"],
    "Negócios e Empreendedorismo": ["Negócios e Empreendedorismo"],
    "Programação": ["Programação"],
    "Trabalho - Petrobras": ["Trabalho - Petrobras"],
    "Casa e Pessoal": ["Casa e Pessoal"],
    "Entretenimento": ["Entretenimento"],
    "Outro": ["Outro"],
}

# Palavras que NUNCA podem virar tag — são plataforma/formato de compartilhamento,
# não assunto. Filtradas tanto no prompt quanto em código (rede de segurança
# para quando o modelo "esquece" a instrução).
BANNED_TAG_WORDS = {
    "instagram", "redes-sociais", "rede-social", "compartilhamento",
    "tiktok", "facebook", "youtube", "twitter", "x", "linkedin",
    "whatsapp", "pinterest", "reels", "shorts", "stories", "story",
    "feed", "post", "video", "link", "compartilhado", "compartilhar",
}

KNOWN_PROJECTS = ["Segunda Mente", "LIBRA", "APLAT", "Media Company"]

CLASSIFICATION_PROMPT = """Você é um bibliotecário digital especialista em organizar uma base de conhecimento pessoal. Analise o conteúdo abaixo e retorne APENAS um JSON válido (sem markdown, sem explicações):

{{
    "title": "Título claro e descritivo em português (max 100 chars)",
    "summary": "Resumo conciso em 2-3 frases em português, focado no que o conteúdo ENSINA ou RESOLVE",
    "category": "Uma EXATAMENTE destas: {categories}",
    "subcategory": "Nome específico da ferramenta, técnica ou tópico (ex: 'Fliki', 'Runway', 'Midjourney', 'Cold Outreach', 'Válvulas de Segurança')",
    "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
    "intent": "Uma de: estudar, assistir, lembrar, ideia, referencia, executar",
    "projects": ["nomes de projetos relacionados"],
    "language": "pt ou en"
}}

Projetos conhecidos: Segunda Mente, LIBRA, APLAT, Media Company.
Interesses do usuário: IA (geração de vídeo/imagem/texto, agentes, automação), marketing digital, negócios digitais, programação, automação industrial (Petrobras P-43).

REGRA MAIS IMPORTANTE — CLASSIFIQUE PELO ASSUNTO, NUNCA PELA PLATAFORMA:
Este conteúdo pode ter chegado via Instagram, TikTok, YouTube, WhatsApp ou qualquer
rede social — isso é só o MEIO de transporte, não o ASSUNTO. Ignore completamente
de onde veio. Classifique pelo que o conteúdo realmente ENSINA, MOSTRA ou VENDE.
Exemplo: um Reels do Instagram sobre uma ferramenta de IA que cria vídeos vai em
"IA - Geração de Vídeo", nunca em "Marketing Digital" só porque veio de rede social.

REGRAS DE TAGS:
- Tags descrevem o CONTEÚDO/ASSUNTO, nunca a plataforma ou o formato onde foi visto.
- PROIBIDO usar como tag: {banned_tags} (e qualquer nome de rede social, app ou formato de post).
- Use nomes de ferramentas, técnicas e conceitos específicos: "geracao-de-video",
  "text-to-video", "clonagem-de-voz", "automacao-marketing", "fliki", "runway",
  "midjourney", "n8n", "prompt-engineering", "cold-outreach", etc.
- Tags em minúsculas, sem acento, sem espaços (use hifens).

OUTRAS REGRAS:
- Se conteúdo em inglês, título e resumo em português.
- Se realmente não se encaixar em nenhuma categoria específica, use "Outro".
- Sempre retorne JSON válido.

Conteúdo:
---
{content}
---"""

ASK_SYSTEM_PROMPT = """Você é a Segunda Mente — o assistente pessoal de conhecimento do Rodrigo.
Você tem acesso à base de conteúdos que ele salvou ao longo do tempo, já com um
score de relevância (0-100) calculado para a pergunta atual.

COMO RESPONDER (regras rígidas):
- Máximo 3-4 frases. Nada de texto longo ou introdução genérica.
- Comece direto pelo número: "Encontrei X conteúdos relevantes sobre [tema]."
- Destaque o(s) resultado(s) de maior score e diga POR QUÊ ele é relevante —
  aponte quantas características do pedido do usuário ele atende, no formato
  "atende N de M pontos que você pediu" quando fizer sentido.
- Referencie os conteúdos pelo título, nunca por ID.
- Termine sugerindo 1-2 termos relacionados para refinar a busca, se fizer sentido.
- Responda SEMPRE em português, mesmo que o conteúdo original esteja em inglês.
- Se não encontrar nada relevante, diga isso em uma frase e sugira reformular a busca.
- Nunca invente conteúdos que não estão na lista fornecida."""

GENERATE_PROMPT_SYSTEM = """Você é um especialista em criar prompts práticos e executáveis para IAs.

Com base no conteúdo abaixo (que é um vídeo/artigo/nota que o usuário salvou), gere um PROMPT DETALHADO E PRÁTICO que o usuário possa copiar e colar em uma IA (Claude, ChatGPT) para EXECUTAR ou IMPLEMENTAR o que está descrito no conteúdo.

O prompt gerado deve:

Ser em português
Ser auto-contido (quem ler o prompt entende o que fazer sem precisar ver o vídeo original)
Incluir passo a passo claro
Especificar ferramentas, tecnologias e recursos mencionados no conteúdo
Pedir à IA que gere algo prático: código, workflow, plano de ação, template, etc.
Ser detalhado o suficiente para que a IA consiga executar sem pedir mais informações

Formato da resposta:
Retorne APENAS o prompt gerado, sem explicações antes ou depois. O prompt deve começar diretamente com a instrução."""
