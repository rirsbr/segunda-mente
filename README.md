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
├── api/                        # Backend FastAPI (Vercel Serverless Functions)
│   ├── index.py                # ÚNICO entrypoint Python — monta o app e todos os routers
│   └── _lib/                   # Lógica de negócio + rotas (ignorado pelo builder da Vercel,
│       │                       # por isso pode conter quantos módulos quisermos)
│       ├── config.py, models.py, supabase_client.py
│       ├── processor.py, ai_service.py, embeddings.py, transcriber.py
│       ├── link_extractor.py, pdf_extractor.py, image_analyzer.py, search.py
│       └── routers/
│           ├── capture.py       # POST /api/capture/*
│           ├── contents.py      # GET/PATCH/DELETE /api/contents
│           ├── search_route.py  # GET /api/search, POST /api/ask
│           ├── projects.py      # GET/POST /api/projects
│           ├── tags.py          # GET /api/tags
│           ├── stats.py         # GET /api/stats
│           └── process.py       # POST /api/process/{id}, /api/process/pending
├── public/                # Frontend estático (servido pela Vercel)
│   ├── index.html, styles.css
│   ├── app.js, capture.js, search.js, library.js, detail.js
│   ├── share.html, share.js    # Web Share Target — recebe conteúdo de outros apps
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

Se o processamento com IA falhar por qualquer motivo (OpenAI fora do ar,
chave inválida, site bloqueando scraping, timeout em arquivo grande), o
conteúdo **já capturado permanece salvo com `status: pending`** — nunca é
perdido e nunca aparece como falha de captura para o usuário. Ele pode ser
reprocessado depois via `POST /api/process/{id}`, exposto no frontend como
o botão **🔄 Reprocessar** na tela de detalhe.

### Por que as rotas ficam em `api/_lib/routers/` e não direto em `api/`

O runtime Python da Vercel trata **todo arquivo `.py` solto dentro de
`/api`** como uma Serverless Function independente, exigindo que ele
exporte uma variável `app` (ASGI) ou `handler`. Módulos como `capture.py`
só exportam um `APIRouter`, então, se ficassem soltos em `/api`, a Vercel
tentaria (e falharia) construí-los como funções próprias — quebrando o
deploy inteiro. A convenção da Vercel é ignorar qualquer arquivo/diretório
prefixado com `_` na hora de detectar funções; por isso todo o código que
não é o entrypoint (`api/index.py`) mora dentro de `api/_lib/`, incluindo
os routers em `api/_lib/routers/`.

## Web Share Target — capturar direto de outros apps

A Segunda Mente aparece na folha de compartilhamento nativa do celular
(YouTube, Instagram, TikTok, Chrome...) quando instalada como PWA. Fluxo:
**compartilhou → capturado → toast de confirmação**, sem copiar/colar.

1. `public/manifest.json` declara `share_target` (`action: /share`,
   `method: POST`, `multipart/form-data`), aceitando `title`, `text`, `url`
   e `files` (imagem, vídeo, áudio, PDF, texto).
2. O navegador faz esse POST direto para `/share` — uma rota que não existe
   no backend (é só uma URL estática). O **Service Worker** (`sw.js`)
   intercepta esse `fetch`, lê o `FormData`, guarda os campos e arquivos no
   IndexedDB e responde com um redirect para `/share.html`.
3. `public/share.html` + `share.js` carregam em contexto de página normal,
   leem o payload do IndexedDB e chamam a API de captura adequada:
   URL → `/api/capture/link`, texto → `/api/capture/text`, cada arquivo →
   `/api/capture/file`. Mostra o resultado e volta para `/` com um toast.
4. `app.js` também aceita compartilhamento via **GET** direto
   (`/?url=...` ou `/?text=...&title=...`), disparando a mesma captura
   automática assim que o app abre — cobre casos de "abrir com" fora do
   fluxo POST do Share Target.

Limitação inerente a esse modelo (hospedagem estática + SW): o POST para
`/share` só é interceptado se o Service Worker já estiver ativo, ou seja,
o app precisa ter sido aberto pelo menos uma vez após a instalação antes
do primeiro compartilhamento funcionar.

## Busca híbrida

`GET /api/search` e `POST /api/ask` combinam busca vetorial (pgvector,
via a função `match_embeddings`) com busca full-text em português (via
`search_contents_fts`), fundidas por **Reciprocal Rank Fusion** (ver
`api/_lib/search.py`). `/api/ask` usa os resultados como contexto para o
GPT-4o-mini responder em linguagem natural, sempre referenciando os
conteúdos encontrados na base.
