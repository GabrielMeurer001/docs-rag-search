CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    slug text PRIMARY KEY,
    title text NOT NULL,
    markdown text NOT NULL,
    origin text NOT NULL,
    revision text NOT NULL
);

CREATE TABLE IF NOT EXISTS chunks (
    id text PRIMARY KEY,
    document_slug text NOT NULL REFERENCES documents(slug) ON DELETE CASCADE,
    section_title text NOT NULL,
    anchor text NOT NULL,
    position integer NOT NULL CHECK (position >= 0),
    excerpt text NOT NULL,
    content_hash text NOT NULL,
    embedding vector(1024) NOT NULL,
    UNIQUE (document_slug, anchor, position)
);

CREATE TABLE IF NOT EXISTS corpus_index (
    singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
    embedding_digest text NOT NULL
);
