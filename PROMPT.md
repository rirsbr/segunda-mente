# SEGUNDA MENTE V4.0

## Sistema Pessoal de Captura, Organização e Busca de Conhecimento com IA

**Deploy**: Vercel (frontend + API routes) + Supabase (banco + storage + vetores)  
**URL**: `segunda-mente-v4.vercel.app` (ou nome personalizado)

---

## VISÃO GERAL

Construir uma aplicação web (PWA) que permita ao usuário:

1. **Capturar** qualquer conteúdo (texto, link, áudio, vídeo, PDF, imagem) de qualquer dispositivo
2. **Processar** automaticamente com IA: transcrever, resumir, classificar, taguear
3. **Armazenar** no Supabase com metadados estruturados e embeddings vetoriais
4. **Buscar** usando linguagem natural, encontrando conteúdos por significado

**Princípio fundamental**: o usuário NÃO organiza nada. Ele joga o conteúdo no sistema e a IA faz todo o trabalho.

---

## STACK TÉCNICA

| Componente | Tecnologia |
|---|---|
| Frontend | HTML + CSS + JavaScript puro (SPA responsiva, sem framework) |
| Backend/API | Vercel Serverless Functions (Python) |
| Banco de dados | Supabase PostgreSQL |
| Busca vetorial | Supabase pgvector |
| Armazenamento de arquivos | Supabase Storage |
| IA - Classificação | OpenAI GPT-4o-mini |
| IA - Transcrição | OpenAI Whisper API |
| IA - Embeddings | OpenAI text-embedding-3-small |
| IA - Chat | OpenAI GPT-4o-mini |
| Metadados de links | yt-dlp (metadados apenas), BeautifulSoup |
| Extração PDF | PyMuPDF (fitz) |
| Deploy | Vercel |

**NÃO usar**: React, Next.js, Node.js, Docker, SQLite, ChromaDB, n8n, Notion, Obsidian.

---

## ESTRUTURA DO PROJETO

```
segunda-mente/
├── PROMPT.md
├── README.md
├── requirements.txt
├── vercel.json
├── .env.example
├── .gitignore
│
├── api/
│   ├── index.py               # FastAPI app principal (mount)
│   ├── _lib/
│   │   ├── __init__.py
│   │   ├── config.py           # Configurações (env vars)
│   │   ├── supabase_client.py  # Cliente Supabase
│   │   ├── models.py           # Pydantic models
│   │   ├── processor.py        # Pipeline de processamento por tipo
│   │   ├── ai_service.py       # OpenAI (resumo, tags, categorias, chat)
│   │   ├── transcriber.py      # Whisper transcrição
│   │   ├── link_extractor.py   # Extração de metadados de URLs
│   │   ├── pdf_extractor.py    # Extração de texto de PDFs
│   │   ├── image_analyzer.py   # Análise de imagens via OpenAI Vision
│   │   ├── search.py           # Busca híbrida (FTS + pgvector)
│   │   └── embeddings.py       # Geração de embeddings
│   │
│   ├── capture.py              # POST /api/capture/* endpoints
│   ├── contents.py             # GET/PATCH/DELETE /api/contents/*
│   ├── search_route.py         # GET /api/search, POST /api/ask
│   ├── projects.py             # GET/POST /api/projects
│   ├── tags.py                 # GET /api/tags
│   ├── stats.py                # GET /api/stats
│   └── process.py              # POST /api/process/{id} (processar pendentes)
│
├── public/
│   ├── index.html              # SPA principal
│   ├── styles.css              # Estilos responsivos (mobile-first)
│   ├── app.js                  # Lógica principal, router, navegação
│   ├── capture.js              # Módulo de captura
│   ├── search.js               # Módulo de busca
│   ├── library.js              # Módulo de biblioteca
│   ├── detail.js               # Módulo de detalhe do conteúdo
│   ├── manifest.json           # PWA manifest
│   ├── sw.js                   # Service worker
│   └── icons/
│       ├── icon-192.png
│       └── icon-512.png
│
└── supabase/
    └── schema.sql              # Script de criação do banco
```

---

## VERCEL CONFIG

### vercel.json

```json
{
    "rewrites": [
        { "source": "/api/(.*)", "destination": "/api/index" }
    ],
    "functions": {
        "api/**/*.py": {
            "runtime": "@vercel/python@4.5.0",
            "maxDuration": 60
        }
    },
    "headers": [
        {
            "source": "/api/(.*)",
            "headers": [
                { "key": "Access-Control-Allow-Origin", "value": "*" },
                { "key": "Access-Control-Allow-Methods", "value": "GET, POST, PATCH, DELETE, OPTIONS" },
                { "key": "Access-Control-Allow-Headers", "value": "Content-Type" }
            ]
        }
    ]
}
```

### api/index.py (mount principal)

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Segunda Mente V4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Importar e incluir routers
from api.capture import router as capture_router
from api.contents import router as contents_router
from api.search_route import router as search_router
from api.projects import router as projects_router
from api.tags import router as tags_router
from api.stats import router as stats_router
from api.process import router as process_router

app.include_router(capture_router, prefix="/api")
app.include_router(contents_router, prefix="/api")
app.include_router(search_router, prefix="/api")
app.include_router(projects_router, prefix="/api")
app.include_router(tags_router, prefix="/api")
app.include_router(stats_router, prefix="/api")
app.include_router(process_router, prefix="/api")

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "4.0"}
```

---

## VARIÁVEIS DE AMBIENTE (Vercel)

Configurar no dashboard do Vercel em Settings > Environment Variables:

```
OPENAI_API_KEY=sk-...
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJ...  (anon/public key)
SUPABASE_SERVICE_KEY=eyJ...  (service role key, para operações admin)
```

### .env.example

```env
OPENAI_API_KEY=sk-your-key-here
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key
```

---

## SUPABASE — CONFIGURAÇÃO

### 1. Criar projeto no Supabase

Ir em https://supabase.com, criar projeto "segunda-mente".

### 2. Habilitar pgvector

No SQL Editor do Supabase, executar:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 3. Criar tabelas

### schema.sql

```sql
-- ===================================
-- SEGUNDA MENTE V4.0 - Schema
-- ===================================

-- Extensão para busca vetorial
CREATE EXTENSION IF NOT EXISTS vector;

-- ===================================
-- TABELA PRINCIPAL: contents
-- ===================================
CREATE TABLE contents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_type TEXT NOT NULL CHECK (content_type IN ('text', 'link', 'audio', 'video', 'pdf', 'image')),
    title TEXT,
    summary TEXT,
    original_text TEXT,
    transcription TEXT,
    extracted_text TEXT,
    source_url TEXT,
    source_platform TEXT,
    category TEXT,
    subcategory TEXT,
    intent TEXT CHECK (intent IN ('estudar', 'assistir', 'lembrar', 'ideia', 'referencia', 'executar', NULL)),
    file_path TEXT,
    file_size BIGINT,
    mime_type TEXT,
    duration INTEGER,
    thumbnail_url TEXT,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'processed', 'error')),
    error_message TEXT,
    is_reviewed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índices
CREATE INDEX idx_contents_type ON contents(content_type);
CREATE INDEX idx_contents_category ON contents(category);
CREATE INDEX idx_contents_status ON contents(status);
CREATE INDEX idx_contents_created ON contents(created_at DESC);
CREATE INDEX idx_contents_reviewed ON contents(is_reviewed);

-- Full-text search index (português)
ALTER TABLE contents ADD COLUMN fts tsvector 
    GENERATED ALWAYS AS (
        setweight(to_tsvector('portuguese', COALESCE(title, '')), 'A') ||
        setweight(to_tsvector('portuguese', COALESCE(summary, '')), 'B') ||
        setweight(to_tsvector('portuguese', COALESCE(original_text, '')), 'C') ||
        setweight(to_tsvector('portuguese', COALESCE(transcription, '')), 'D') ||
        setweight(to_tsvector('portuguese', COALESCE(extracted_text, '')), 'D')
    ) STORED;

CREATE INDEX idx_contents_fts ON contents USING gin(fts);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER contents_updated_at
    BEFORE UPDATE ON contents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ===================================
-- TABELA: tags
-- ===================================
CREATE TABLE tags (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL
);

-- ===================================
-- TABELA: content_tags
-- ===================================
CREATE TABLE content_tags (
    content_id UUID REFERENCES contents(id) ON DELETE CASCADE,
    tag_id INTEGER REFERENCES tags(id) ON DELETE CASCADE,
    confidence REAL DEFAULT 1.0,
    PRIMARY KEY (content_id, tag_id)
);

-- ===================================
-- TABELA: projects
-- ===================================
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Projetos iniciais
INSERT INTO projects (name, description) VALUES
    ('Segunda Mente', 'Sistema pessoal de conhecimento'),
    ('LIBRA', 'App de cofres de bloqueio P-43'),
    ('APLAT', 'Automações da plataforma P-43'),
    ('Media Company', 'Projeto de blogs com IA'),
    ('Geral', 'Conteúdos sem projeto específico');

-- ===================================
-- TABELA: content_projects
-- ===================================
CREATE TABLE content_projects (
    content_id UUID REFERENCES contents(id) ON DELETE CASCADE,
    project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
    PRIMARY KEY (content_id, project_id)
);

-- ===================================
-- TABELA: embeddings
-- ===================================
CREATE TABLE content_embeddings (
    id SERIAL PRIMARY KEY,
    content_id UUID REFERENCES contents(id) ON DELETE CASCADE,
    embedding vector(1536),
    chunk_text TEXT,
    chunk_index INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Índice HNSW para busca vetorial rápida
CREATE INDEX idx_embeddings_vector ON content_embeddings 
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX idx_embeddings_content ON content_embeddings(content_id);

-- ===================================
-- FUNÇÃO: busca vetorial
-- ===================================
CREATE OR REPLACE FUNCTION match_embeddings(
    query_embedding vector(1536),
    match_threshold float DEFAULT 0.3,
    match_count int DEFAULT 20
)
RETURNS TABLE (
    content_id UUID,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        ce.content_id,
        1 - (ce.embedding <=> query_embedding) AS similarity
    FROM content_embeddings ce
    WHERE 1 - (ce.embedding <=> query_embedding) > match_threshold
    ORDER BY ce.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

-- ===================================
-- FUNÇÃO: busca full-text
-- ===================================
CREATE OR REPLACE FUNCTION search_contents_fts(
    search_query TEXT,
    max_results INT DEFAULT 20
)
RETURNS TABLE (
    id UUID,
    rank REAL
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id,
        ts_rank(c.fts, websearch_to_tsquery('portuguese', search_query))::REAL AS rank
    FROM contents c
    WHERE c.fts @@ websearch_to_tsquery('portuguese', search_query)
    ORDER BY rank DESC
    LIMIT max_results;
END;
$$;

-- ===================================
-- SUPABASE STORAGE
-- ===================================
-- Criar bucket via Dashboard ou API:
-- Nome: "files"
-- Public: false
-- File size limit: 100MB
-- Allowed MIME types: todos
```

### 4. Criar Storage Bucket

No Supabase Dashboard: Storage > Create Bucket > nome "files", privado, 100MB limit.

---

## CATEGORIAS PRÉ-DEFINIDAS

```python
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
```

---

## API ENDPOINTS

Todos servidos via Vercel Serverless Functions (Python/FastAPI).

### Captura

```
POST /api/capture/text
Body: { "text": "string", "context": "string opcional" }
→ Cria registro, inicia processamento, retorna { id, status: "processing" }

POST /api/capture/link
Body: { "url": "string", "note": "string opcional" }
→ Extrai metadados do link, cria registro, processa

POST /api/capture/file
Multipart: file + note (opcional)
Aceita: áudio (mp3, wav, ogg, m4a, webm), vídeo (mp4, webm),
        PDF, imagem (jpg, png, webp), documento (txt, md)
→ Upload para Supabase Storage, cria registro, processa

POST /api/capture/audio
Multipart: audio (gravado pelo browser via MediaRecorder)
→ Upload, transcreve via Whisper, classifica
```

### Busca

```
GET /api/search?q={query}&type={tipo}&category={cat}&from={data}&to={data}&reviewed={bool}&limit=20&offset=0

Retorna:
{
    "results": [{ id, content_type, title, summary, category, tags, created_at, is_reviewed }],
    "total": 42
}
```

### Chat / Busca Inteligente

```
POST /api/ask
Body: { "question": "O que eu tenho sobre agentes de IA?" }

Retorna:
{
    "answer": "Você tem 12 conteúdos sobre agentes de IA...",
    "contents": [top 5 resultados],
    "total_found": 12
}
```

### Biblioteca

```
GET /api/contents?type=&category=&status=&sort=created_at&order=desc&limit=20&offset=0
GET /api/contents/{id}
PATCH /api/contents/{id}   Body: { "is_reviewed": true } ou { "title": "novo" }
DELETE /api/contents/{id}
```

### Stats

```
GET /api/stats
Retorna:
{
    "total": 142,
    "by_type": { "video": 12, "link": 34, "text": 56, ... },
    "by_category": { "IA": 45, "Programação": 23, ... },
    "pending": 3,
    "unreviewed": 23,
    "recent_7d": 18,
    "top_tags": [{ "name": "ia", "count": 34 }, ...]
}
```

### Projetos e Tags

```
GET /api/projects
POST /api/projects   Body: { "name": "string", "description": "string" }
GET /api/tags
```

### Processamento (reprocessar pendentes/erros)

```
POST /api/process/{id}
→ Re-processa um conteúdo com status 'pending' ou 'error'

POST /api/process/pending
→ Processa todos os pendentes (chamado por cron ou manualmente)
```

---

## PIPELINE DE PROCESSAMENTO

### Fluxo geral

```
Conteúdo recebido
    │
    ▼
1. Salvar registro (status: pending)
    │
    ▼
2. Se arquivo → upload para Supabase Storage
    │
    ▼
3. Extrair conteúdo textual
    │  ├── Link: yt-dlp metadata / BeautifulSoup
    │  ├── Áudio: OpenAI Whisper API
    │  ├── Vídeo: OpenAI Whisper API (áudio extraído)
    │  ├── PDF: PyMuPDF texto
    │  ├── Imagem: OpenAI Vision API
    │  └── Texto: usar direto
    │
    ▼
4. Classificar com LLM (GPT-4o-mini)
    │  → título, resumo, categoria, subcategoria, tags, intenção, projetos
    │
    ▼
5. Gerar embedding (text-embedding-3-small)
    │  → salvar em content_embeddings
    │
    ▼
6. Atualizar registro (status: processed)
```

### IMPORTANTE sobre Vercel Serverless

Como as funções serverless têm timeout (60s no plano Pro), o processamento é feito **de forma síncrona dentro da mesma request** de captura. O fluxo é:

1. Request POST /api/capture/text chega
2. Cria registro no banco (status: pending)
3. Na MESMA request, processa: classifica com LLM + gera embedding
4. Atualiza status para processed
5. Retorna resultado

Para arquivos grandes (áudio/vídeo) que podem demorar mais:

1. Request POST /api/capture/file chega
2. Upload do arquivo para Supabase Storage
3. Cria registro no banco (status: pending)
4. Tenta processar na mesma request
5. Se der timeout → status fica como 'pending'
6. O endpoint POST /api/process/{id} permite reprocessar depois
7. O frontend mostra botão "Reprocessar" para itens pendentes

### Prompt de classificação

```python
CLASSIFICATION_PROMPT = """Você é um assistente de organização pessoal. Analise o conteúdo abaixo e retorne APENAS um JSON válido (sem markdown, sem explicações):

{
    "title": "Título claro e descritivo em português (max 100 chars)",
    "summary": "Resumo conciso em 2-3 frases em português",
    "category": "Uma das: Inteligência Artificial, Programação, Negócios, Trabalho, Pessoal, Outros",
    "subcategory": "Subcategoria específica",
    "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
    "intent": "Uma de: estudar, assistir, lembrar, ideia, referencia, executar",
    "projects": ["nomes de projetos relacionados"],
    "language": "pt ou en"
}

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
```

---

## BUSCA HÍBRIDA

```python
async def hybrid_search(query: str, filters: dict, limit: int = 20):
    # 1. Gerar embedding da query
    query_embedding = await get_embedding(query)

    # 2. Busca vetorial via pgvector
    vector_results = supabase.rpc("match_embeddings", {
        "query_embedding": query_embedding,
        "match_threshold": 0.3,
        "match_count": limit
    }).execute()

    # 3. Busca full-text via PostgreSQL
    fts_results = supabase.rpc("search_contents_fts", {
        "search_query": query,
        "max_results": limit
    }).execute()

    # 4. Reciprocal Rank Fusion (combinar scores)
    combined = reciprocal_rank_fusion(
        vector_ids=[(r["content_id"], r["similarity"]) for r in vector_results.data],
        fts_ids=[(r["id"], r["rank"]) for r in fts_results.data],
        k=60
    )

    # 5. Buscar conteúdos completos dos IDs combinados
    content_ids = [c[0] for c in combined[:limit]]
    contents = supabase.table("contents").select("*").in_("id", content_ids).execute()

    # 6. Aplicar filtros (type, category, date, reviewed)
    filtered = apply_filters(contents.data, filters)

    # 7. Manter ordem do ranking
    id_order = {id: i for i, (id, _) in enumerate(combined)}
    filtered.sort(key=lambda c: id_order.get(c["id"], 999))

    return filtered


def reciprocal_rank_fusion(vector_ids, fts_ids, k=60):
    """Combina dois rankings usando RRF"""
    scores = {}
    for rank, (id, _) in enumerate(vector_ids):
        scores[id] = scores.get(id, 0) + 1 / (k + rank + 1)
    for rank, (id, _) in enumerate(fts_ids):
        scores[id] = scores.get(id, 0) + 1 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

---

## ENDPOINT /api/ask — CHAT COM A BASE

```python
async def ask(question: str):
    # 1. Buscar conteúdos relevantes
    results = await hybrid_search(question, {}, limit=10)

    # 2. Montar contexto
    context_parts = []
    for r in results[:8]:
        context_parts.append(
            f"[{r['content_type'].upper()}] {r['title']}\n"
            f"Categoria: {r['category']}\n"
            f"Resumo: {r['summary']}\n"
            f"Data: {r['created_at']}\n"
        )
    context = "\n---\n".join(context_parts)

    # 3. Perguntar ao LLM
    response = await openai_chat(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": """Você é a Segunda Mente — o assistente pessoal de conhecimento do Rodrigo.
Você tem acesso à base de conteúdos que ele salvou ao longo do tempo.
Responda de forma direta, útil e em português.
Referencie os conteúdos encontrados pelo título.
Se não encontrar nada relevante, diga isso claramente.
Não invente conteúdos que não estão na base."""},
            {"role": "user", "content": f"""Pergunta: {question}

Conteúdos encontrados na base ({len(results)} resultados):
{context}

Responda a pergunta usando os conteúdos acima."""}
        ]
    )

    return {
        "answer": response,
        "contents": results[:5],
        "total_found": len(results)
    }
```

---

## FRONTEND — INTERFACE WEB RESPONSIVA

### Design: Mobile-First, Dark Theme

3 telas acessadas por barra de navegação inferior (mobile) ou lateral (desktop).

### Tela 1: CAPTURA (ícone: ➕)

```
┌────────────────────────────────┐
│  🧠 SEGUNDA MENTE             │
│                                │
│  ┌────────────────────────┐    │
│  │                        │    │
│  │  Cole um link,         │    │
│  │  escreva uma nota,     │    │
│  │  ou arraste um arquivo │    │
│  │                        │    │
│  └────────────────────────┘    │
│                                │
│  ┌────┐ ┌────┐ ┌────┐ ┌────┐  │
│  │ 📎 │ │ 🎙 │ │ 📷 │ │ 🔗 │  │
│  │Arq.│ │Áud.│ │Foto│ │Link│  │
│  └────┘ └────┘ └────┘ └────┘  │
│                                │
│  [     CAPTURAR      ]        │
│                                │
│  ── Últimas capturas ──       │
│  📝 Nota sobre agentes  2min  │
│  🎥 Vídeo Veo 4         1h   │
│  🔗 Link n8n            3h   │
│                                │
│ ┌──────┐ ┌──────┐ ┌──────┐   │
│ │  ➕  │ │  🔍  │ │  📚  │   │
│ │Captur│ │Busca │ │Biblio│   │
│ └──────┘ └──────┘ └──────┘   │
└────────────────────────────────┘
```

**Funcionalidades de captura:**
- **Área de texto** (textarea): aceita texto livre e detecta URLs automaticamente
- **Botão Arquivo** (📎): input type="file" accept="*/*" — aceita qualquer arquivo
- **Botão Áudio** (🎙): grava áudio via MediaRecorder API do browser. Mostra visualização de onda durante gravação. Botão vermelho pulsante para gravar, botão de parar.
- **Botão Foto** (📷): input type="file" accept="image/*" capture="environment" — abre câmera no mobile
- **Botão Link** (🔗): abre campo específico para URL com validação
- **Drag & drop**: arrastar arquivos para a área central (desktop)
- **Botão CAPTURAR**: envia o conteúdo. Mostra toast com feedback: "Capturado! Processando..."
- **Lista recentes**: últimas 5 capturas com ícone do tipo, título (ou preview), tempo relativo
- **Auto-detect**: se o texto colado é uma URL, tratar como link automaticamente

### Tela 2: BUSCA (ícone: 🔍)

```
┌────────────────────────────────┐
│  🔍 Pergunte à Segunda Mente  │
│                                │
│  ┌────────────────────────┐    │
│  │ O que eu tenho sobre...│    │
│  └────────────────────────┘    │
│                                │
│  Filtros:                      │
│  [Todos▾] [Todas categorias▾]  │
│                                │
│  ── Resposta da IA ──         │
│  "Encontrei 12 conteúdos..."  │
│                                │
│  ── Resultados ──             │
│  ┌────────────────────────┐    │
│  │ 🎥 Como criar agentes │    │
│  │ IA > Agentes • 2 dias │    │
│  │ "Vídeo explicando..."  │    │
│  └────────────────────────┘    │
│  ┌────────────────────────┐    │
│  │ 📝 Ideia: agente LIBRA│    │
│  │ Trabalho • 5 dias      │    │
│  │ "Automatizar o..."     │    │
│  └────────────────────────┘    │
│                                │
│ ┌──────┐ ┌──────┐ ┌──────┐   │
│ │  ➕  │ │  🔍  │ │  📚  │   │
│ └──────┘ └──────┘ └──────┘   │
└────────────────────────────────┘
```

**Funcionalidades:**
- Campo de busca em linguagem natural (Enter ou botão para buscar)
- Primeiro faz busca semântica (/api/ask) → mostra resposta da IA + resultados
- Filtros dropdown: tipo (todos, vídeo, link, texto, áudio, pdf, imagem) e categoria
- Cards de resultado: ícone tipo, título, categoria + subcategoria, tempo relativo, resumo truncado (2 linhas)
- Clicar no card → abre tela de detalhe (modal ou navegação)

### Tela 3: BIBLIOTECA (ícone: 📚)

```
┌────────────────────────────────┐
│  📚 Biblioteca                 │
│                                │
│  142 conteúdos • 23 não vistos│
│                                │
│  [All] [🎥12] [🔗34] [📝56]  │
│  [🎙8] [📄15] [📷17]         │
│                                │
│  Ordenar: [Mais recentes ▾]   │
│                                │
│  ┌────────────────────────┐    │
│  │ 🎥 Criar agentes IA   │    │
│  │ IA > Agentes           │    │
│  │ 2 dias • ⬜ não visto  │    │
│  │ #agentes #ia #automacao│    │
│  └────────────────────────┘    │
│  ┌────────────────────────┐    │
│  │ 📝 Ideia Media Company│    │
│  │ Negócios > Marketing   │    │
│  │ 3 dias • ✅ visto      │    │
│  │ #marketing #afiliados  │    │
│  └────────────────────────┘    │
│  ... (scroll infinito)        │
│                                │
│ ┌──────┐ ┌──────┐ ┌──────┐   │
│ │  ➕  │ │  🔍  │ │  📚  │   │
│ └──────┘ └──────┘ └──────┘   │
└────────────────────────────────┘
```

**Funcionalidades:**
- Contadores no topo (total e não revisados)
- Filtros rápidos por tipo (botões horizontais com scroll, cada um com contador)
- Dropdown de categoria
- Dropdown de ordenação: mais recentes, mais antigos, não revisados primeiro
- Cards com: ícone tipo, título, categoria/subcategoria, tempo relativo, status revisão, tags
- Scroll infinito (carregar mais 20 ao chegar no final)
- Clicar no card → detalhe

### Tela de Detalhe (modal overlay)

```
┌────────────────────────────────┐
│  ← Voltar              🗑️     │
│                                │
│  🎥 Como criar agentes de IA  │
│                                │
│  Categoria: IA > Agentes       │
│  Capturado: 24/07/2026         │
│  Intenção: Estudar             │
│  Status: ⬜ Não revisado       │
│                                │
│  ── Resumo ──                  │
│  "Este vídeo explica como..."  │
│                                │
│  ── Tags ──                    │
│  #agentes #ia #mcp #rag        │
│                                │
│  ── Projetos ──                │
│  Segunda Mente • LIBRA         │
│                                │
│  ── Transcrição ──             │
│  [▼ Expandir completa]         │
│                                │
│  ── Fonte ──                   │
│  🔗 youtube.com/watch?v=...    │
│                                │
│  [✅ Marcar revisado]          │
│  [🔄 Reprocessar]              │
│                                │
└────────────────────────────────┘
```

### Design System

```css
/* ===================================
   SEGUNDA MENTE V4.0 — Design System
   =================================== */

:root {
    /* Cores - Dark Theme */
    --bg-primary: #0a0a0f;
    --bg-secondary: #12121a;
    --bg-card: #1a1a28;
    --bg-card-hover: #22223a;
    --bg-input: #15151f;
    --bg-nav: #0d0d14;

    --accent: #6c5ce7;
    --accent-light: #a29bfe;
    --accent-glow: rgba(108, 92, 231, 0.15);

    --text-primary: #e8e8f0;
    --text-secondary: #9090a8;
    --text-muted: #5a5a72;

    --success: #00cec9;
    --warning: #fdcb6e;
    --error: #ff6b6b;
    --info: #74b9ff;

    --border: #2a2a3e;
    --border-focus: var(--accent);

    /* Tipografia */
    --font-main: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
    --font-mono: 'JetBrains Mono', 'Fira Code', monospace;

    /* Tamanhos */
    --radius: 12px;
    --radius-sm: 8px;
    --radius-lg: 16px;

    /* Shadows */
    --shadow-card: 0 2px 12px rgba(0, 0, 0, 0.3);
    --shadow-modal: 0 8px 32px rgba(0, 0, 0, 0.5);

    /* Nav height (para padding-bottom do conteúdo) */
    --nav-height: 64px;
}

/* Mobile-first base */
* { box-sizing: border-box; margin: 0; padding: 0; }

body {
    font-family: var(--font-main);
    background: var(--bg-primary);
    color: var(--text-primary);
    min-height: 100vh;
    -webkit-font-smoothing: antialiased;
}

/* Tipo ícones */
.type-icon {
    /* Usar emojis: 📝 texto, 🔗 link, 🎙 áudio, 🎥 vídeo, 📄 pdf, 📷 imagem */
}

/* Botões de ação */
.btn-primary {
    background: var(--accent);
    color: white;
    border: none;
    padding: 12px 24px;
    border-radius: var(--radius);
    font-size: 16px;
    font-weight: 600;
    cursor: pointer;
    width: 100%;
    transition: all 0.2s;
}

/* Cards de conteúdo */
.content-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px;
    margin-bottom: 12px;
    cursor: pointer;
    transition: all 0.2s;
}
.content-card:hover {
    background: var(--bg-card-hover);
    border-color: var(--accent);
}

/* Nav inferior (mobile) */
.bottom-nav {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    height: var(--nav-height);
    background: var(--bg-nav);
    border-top: 1px solid var(--border);
    display: flex;
    justify-content: space-around;
    align-items: center;
    z-index: 100;
    padding-bottom: env(safe-area-inset-bottom);
}

/* Tags */
.tag {
    display: inline-block;
    background: var(--accent-glow);
    color: var(--accent-light);
    padding: 4px 10px;
    border-radius: 20px;
    font-size: 12px;
    margin: 2px;
}

/* Toast / Notificação */
.toast {
    position: fixed;
    top: 20px;
    right: 20px;
    padding: 12px 20px;
    border-radius: var(--radius-sm);
    z-index: 1000;
    animation: slideIn 0.3s ease;
}
.toast-success { background: var(--success); color: #000; }
.toast-error { background: var(--error); color: #fff; }
.toast-info { background: var(--info); color: #000; }

/* Gravação de áudio */
.recording-indicator {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: var(--error);
    animation: pulse 1s infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.6; transform: scale(1.2); }
}

/* Responsivo */
@media (min-width: 768px) {
    /* Desktop: nav lateral, conteúdo centralizado */
    .bottom-nav {
        top: 0;
        bottom: 0;
        right: auto;
        width: 72px;
        flex-direction: column;
        border-top: none;
        border-right: 1px solid var(--border);
        padding-bottom: 0;
    }
    .main-content {
        margin-left: 72px;
        max-width: 720px;
        margin-inline: auto;
        padding: 24px;
    }
}
```

### PWA

**manifest.json:**
```json
{
    "name": "Segunda Mente",
    "short_name": "2ª Mente",
    "description": "Seu segundo cérebro pessoal com IA",
    "start_url": "/",
    "display": "standalone",
    "background_color": "#0a0a0f",
    "theme_color": "#6c5ce7",
    "icons": [
        { "src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
        { "src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png" }
    ]
}
```

**sw.js** — cachear apenas os assets estáticos (HTML, CSS, JS, ícones). As chamadas API passam direto para a rede.

### Gravação de Áudio no Browser

```javascript
// Usar MediaRecorder API
let mediaRecorder;
let audioChunks = [];

async function startRecording() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });

    mediaRecorder.ondataavailable = (e) => audioChunks.push(e.data);
    mediaRecorder.onstop = async () => {
        const blob = new Blob(audioChunks, { type: 'audio/webm' });
        audioChunks = [];
        await uploadAudio(blob);
    };

    mediaRecorder.start();
}

function stopRecording() {
    mediaRecorder.stop();
    mediaRecorder.stream.getTracks().forEach(t => t.stop());
}

async function uploadAudio(blob) {
    const formData = new FormData();
    formData.append('audio', blob, 'recording.webm');
    const res = await fetch('/api/capture/audio', { method: 'POST', body: formData });
    const data = await res.json();
    showToast('Áudio capturado! Processando...', 'success');
}
```

### Auto-detecção de URL

```javascript
function detectContentType(text) {
    const urlRegex = /https?:\/\/[^\s]+/g;
    const urls = text.match(urlRegex);
    if (urls && urls.length === 1 && text.trim() === urls[0]) {
        return { type: 'link', url: urls[0] };
    }
    if (urls && urls.length >= 1) {
        return { type: 'text_with_links', text, urls };
    }
    return { type: 'text', text };
}
```

---

## SUPABASE CLIENT (Python)

```python
# api/_lib/supabase_client.py
from supabase import create_client
import os

def get_supabase():
    return create_client(
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_KEY"]
    )
```

---

## REQUIREMENTS.TXT

```
fastapi>=0.115.0
uvicorn>=0.27.0
python-multipart>=0.0.9
httpx>=0.27.0
openai>=1.30.0
yt-dlp>=2024.1.1
PyMuPDF>=1.24.0
supabase>=2.5.0
python-dotenv>=1.0.0
beautifulsoup4>=4.12.0
pillow>=10.0.0
pydantic>=2.5.0
aiofiles>=23.2.0
```

---

## DEPLOY NO VERCEL

### Passo a passo

1. Criar projeto no GitHub
2. Push do código
3. Conectar no Vercel (vercel.com → Import Project)
4. Configurar Environment Variables no Vercel Dashboard:
   - `OPENAI_API_KEY`
   - `SUPABASE_URL`
   - `SUPABASE_KEY`
   - `SUPABASE_SERVICE_KEY`
5. Deploy automático

### Resultado

URL pública: `https://segunda-mente-v4.vercel.app`

Acessível de qualquer lugar:
- Celular (adicionar à tela inicial = PWA)
- Notebook
- PC do trabalho
- Qualquer browser

---

## O QUE NÃO ESTÁ NO MVP (futuro)

- Importação de export do WhatsApp (Fase 2)
- Integração direta com WhatsApp
- Obsidian sync
- Agente proativo (resumo semanal)
- Dashboard com gráficos
- Sistema de scoring/recomendação
- Detecção de duplicados
- Autenticação (se necessário)
- Processamento em background (Supabase Edge Functions)
