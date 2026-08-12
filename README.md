# Segunda Mente V4.0

Sistema pessoal de captura, organização e busca de conhecimento com IA.

Jogue qualquer conteúdo no sistema — texto, link, áudio, vídeo, PDF ou imagem
— e a IA cuida de transcrever, resumir, classificar, taguear e indexar para
busca semântica. Você nunca organiza nada manualmente.

Veja a especificação completa em [`PROMPT.md`](./PROMPT.md).

---

## Stack

- **Frontend**: HTML + CSS + JavaScript puro (SPA responsiva, mobile-first, PWA)
- **Backend**: Vercel Serverless Functions (Python + FastAPI)
- **Banco**: Supabase PostgreSQL + pgvector
- **Storage**: Supabase Storage
- **IA**: OpenAI (GPT-4o-mini para classificação/chat, Whisper para transcrição,
  text-embedding-3-small para embeddings, Vision para imagens)

Sem React, Next.js, Node.js no backend, Docker, SQLite ou ChromaDB.

---

## Estrutura

```
segunda-mente/
├── api/                  # Backend FastAPI (Vercel Serverless Functions)
│   ├── index.py          # App principal (mount de todos os routers)
│   ├── _lib/              # Lógica de negócio (config, IA, extração, busca...)
│   ├── capture.py         # POST /api/capture/*
│   ├── contents.py        # GET/PATCH/DELETE /api/contents
│   ├── search_route.py    # GET /api/search, POST /api/ask
│   ├── projects.py        # GET/POST /api/projects
│   ├── tags.py             # GET /api/tags
│   ├── stats.py            # GET /api/stats
│   └── process.py          # POST /api/process/{id}, /api/process/pending
├── public/                # Frontend estático (servido pela Vercel)
│   ├── index.html, styles.css
│   ├── app.js, capture.js, search.js, library.js, detail.js
│   ├── manifest.json, sw.js
│   └── icons/
├── supabase/schema.sql    # Schema completo (tabelas, índices, funções RPC)
├── build_icons.py         # Gera os ícones PWA (public/icons/*.png)
├── vercel.json
├── requirements.txt
└── .env.example
```

---

## Configuração

### 1. Supabase

1. Criar um projeto em [supabase.com](https://supabase.com).
2. No SQL Editor, executar o conteúdo de [`supabase/schema.sql`](./supabase/schema.sql).
   Isso habilita a extensão `pgvector`, cria as tabelas (`contents`, `tags`,
   `content_tags`, `projects`, `content_projects`, `content_embeddings`) e as
   funções `match_embeddings` (busca vetorial) e `search_contents_fts`
   (busca full-text em português).
3. Em **Storage**, criar um bucket chamado `files` (privado, limite de 100MB).

### 2. Variáveis de ambiente

Copiar `.env.example` para `.env` (uso local) e/ou configurar no dashboard da
Vercel em **Settings > Environment Variables**:

```env
OPENAI_API_KEY=sk-...
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJ...              # anon/public key
SUPABASE_SERVICE_KEY=eyJ...      # service role key (usada pelo backend)
```

### 3. Deploy

1. Push do repositório para o GitHub.
2. Importar o projeto no [Vercel](https://vercel.com) (New Project → Import).
3. Configurar as variáveis de ambiente acima.
4. Deploy automático — o `vercel.json` já cuida do roteamento de `/api/*`
   para as Serverless Functions em Python e do servimento estático de `public/`.

A URL pública funciona em qualquer navegador e pode ser "Adicionada à Tela
Inicial" no celular como PWA (instalação via `manifest.json` + `sw.js`).

---

## Desenvolvimento local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Rodar a API localmente com uvicorn (equivalente ao ambiente da Vercel)
uvicorn api.index:app --reload --port 8000

# Servir o frontend estático (em outro terminal)
cd public && python3 -m http.server 5500
```

Para gerar novamente os ícones PWA:

```bash
python3 build_icons.py
```

---

## Pipeline de processamento

Toda captura roda o mesmo fluxo, síncrono dentro da própria request (ver
`api/_lib/processor.py`):

1. Cria o registro em `contents` (`status: pending`).
2. Se for arquivo, faz upload para o Supabase Storage.
3. Extrai o conteúdo textual conforme o tipo:
   - **Link**: `yt-dlp` (plataformas de vídeo conhecidas) ou BeautifulSoup (páginas genéricas)
   - **Áudio/Vídeo**: OpenAI Whisper
   - **PDF**: PyMuPDF
   - **Imagem**: OpenAI Vision
   - **Texto**: usado diretamente
4. Classifica com GPT-4o-mini (título, resumo, categoria, subcategoria, tags, intenção, projetos).
5. Gera embeddings (`text-embedding-3-small`) e salva em `content_embeddings`.
6. Atualiza o registro (`status: processed`).

Se o processamento falhar ou expirar (arquivos grandes), o conteúdo fica
`pending`/`error` e pode ser reprocessado via `POST /api/process/{id}` — o
frontend expõe isso como o botão **🔄 Reprocessar** na tela de detalhe.

## Busca híbrida

`GET /api/search` e `POST /api/ask` combinam busca vetorial (pgvector,
via a função `match_embeddings`) com busca full-text em português (via
`search_contents_fts`), fundidas por **Reciprocal Rank Fusion** (ver
`api/_lib/search.py`). `/api/ask` usa os resultados como contexto para o
GPT-4o-mini responder em linguagem natural, sempre referenciando os
conteúdos encontrados na base.
