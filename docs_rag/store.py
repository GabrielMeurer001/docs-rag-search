from dataclasses import dataclass
from pathlib import Path

import psycopg
from pgvector.psycopg import register_vector
from psycopg.rows import class_row

from .markdown import Document, chunks_for

SCHEMA = Path(__file__).with_name("schema.sql")
INDEX_LOCK = 774721943


@dataclass(frozen=True)
class Retrieved:
    chunk_id: str
    document_slug: str
    document_title: str
    section_title: str
    anchor: str
    excerpt: str

    @property
    def url(self):
        return f"/guia/{self.document_slug}#{self.anchor}"


@dataclass(frozen=True)
class IndexStats:
    chunks: int
    embedded: int
    embedding_digest: str


class IndexUnavailable(Exception):
    pass


class Store:
    def __init__(self, database_url: str):
        self.database_url = database_url

    def connect(self):
        return psycopg.connect(
            self.database_url, connect_timeout=3, options="-c statement_timeout=5000",
        )

    def index(self, documents: list[Document], models) -> IndexStats:
        entries = [(document, chunk) for document in documents for chunk in chunks_for(document)]
        with self.connect() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(%s)", (INDEX_LOCK,))
            conn.execute(SCHEMA.read_text(encoding="utf-8"))
            register_vector(conn)
            digest = models.embedding_digest()
            embeddings = dict(conn.execute(
                """SELECT content_hash, embedding FROM chunks
                   WHERE EXISTS (SELECT 1 FROM corpus_index WHERE embedding_digest = %s)""",
                (digest,),
            ).fetchall())
            missing = {
                chunk.content_hash: chunk.embedding_text for _, chunk in entries
                if chunk.content_hash not in embeddings
            }
            if missing:
                items = list(missing.items())
                for offset in range(0, len(items), 16):
                    batch = items[offset:offset + 16]
                    vectors = models.embed([value for _, value in batch])
                    embeddings.update(zip((key for key, _ in batch), vectors, strict=True))
                if models.embedding_digest() != digest:
                    raise IndexUnavailable("O modelo de embeddings mudou durante a indexação")

            # Readers continue seeing the previous snapshot until the transaction commits.
            conn.execute("DELETE FROM documents")
            with conn.cursor() as cursor:
                cursor.executemany(
                    """INSERT INTO documents (slug, title, markdown, origin, revision)
                       VALUES (%s, %s, %s, %s, %s)""",
                    [(doc.slug, doc.title, doc.markdown, doc.origin, doc.revision) for doc in documents],
                )
                cursor.executemany(
                    """INSERT INTO chunks
                       (id, document_slug, section_title, anchor, position, excerpt, content_hash, embedding)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    [
                        (chunk.id, doc.slug, chunk.section_title, chunk.anchor, chunk.position,
                         chunk.excerpt, chunk.content_hash, embeddings[chunk.content_hash])
                        for doc, chunk in entries
                    ],
                )
            conn.execute(
                """INSERT INTO corpus_index (embedding_digest) VALUES (%s)
                   ON CONFLICT (singleton) DO UPDATE SET embedding_digest = EXCLUDED.embedding_digest""",
                (digest,),
            )
        return IndexStats(len(entries), len(missing), digest)

    def retrieve(self, embedding, digest: str) -> list[Retrieved]:
        with self.connect() as conn:
            register_vector(conn)
            with conn.cursor(row_factory=class_row(Retrieved)) as cursor:
                rows = cursor.execute(
                    """SELECT c.id AS chunk_id, d.slug AS document_slug, d.title AS document_title,
                              c.section_title, c.anchor, c.excerpt
                       FROM chunks c JOIN documents d ON d.slug = c.document_slug
                       WHERE EXISTS (SELECT 1 FROM corpus_index WHERE embedding_digest = %s)
                       ORDER BY c.embedding <=> %s, c.id LIMIT 3""",
                    (digest, embedding),
                ).fetchall()
        if not rows:
            raise IndexUnavailable("Corpus ainda indisponível ou modelo de embeddings incompatível")
        return rows

    def document(self, slug: str) -> Document | None:
        with self.connect() as conn, conn.cursor(row_factory=class_row(Document)) as cursor:
            return cursor.execute(
                "SELECT slug, title, markdown, origin, revision FROM documents WHERE slug = %s",
                (slug,),
            ).fetchone()
