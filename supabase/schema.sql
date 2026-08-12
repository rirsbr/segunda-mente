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
