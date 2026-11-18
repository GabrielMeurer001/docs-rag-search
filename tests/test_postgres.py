import os
from uuid import uuid4

import numpy as np
import psycopg
import pytest
from psycopg import sql

from docs_rag.config import DIMENSIONS
from docs_rag.markdown import Document
from docs_rag.models import ModelFailure
from docs_rag.store import IndexUnavailable, Store

pytestmark = pytest.mark.postgres


@pytest.fixture
def store():
    url = os.getenv("DOCS_RAG_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Configure DOCS_RAG_TEST_DATABASE_URL para testar com PostgreSQL")
    schema = sql.Identifier(f"docs_rag_test_{uuid4().hex}")

    class IsolatedStore(Store):
        def connect(self):
            conn = super().connect()
            conn.execute(sql.SQL("SET search_path TO {}, public").format(schema))
            return conn

    with psycopg.connect(url, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE SCHEMA {}").format(schema))
        try:
            yield IsolatedStore(url)
        finally:
            admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(schema))


class FakeModels:
    digest = "v1"
    fail = False

    def embedding_digest(self):
        return self.digest

    def embed(self, texts):
        if self.fail:
            raise ModelFailure("simulated")
        vectors = []
        for text in texts:
            vector = np.zeros(DIMENSIONS, dtype=np.float32)
            vector[0 if "mais próximo" in text else 1] = 1
            vectors.append(vector)
        return vectors


def doc(markdown):
    return Document("csv", "Manual", markdown, "worker", "abc")


def test_index_snapshot_reuse_ranking_update_and_rollback(store):
    original = doc("## A {#a}\n\nTexto distante.\n\n## B {#b}\n\nTexto mais próximo.")
    updated = doc("## B {#b}\n\nTexto mais próximo, revisado.")
    models = FakeModels()
    assert store.index([original], models).embedded == 2
    repeated = store.index([original], models)
    assert (repeated.chunks, repeated.embedded) == (2, 0)
    query, = models.embed(["mais próximo"])
    assert [row.chunk_id for row in store.retrieve(query, "v1")] == ["csv:b:0", "csv:a:0"]
    assert store.document("csv") == original

    models.fail = True
    with pytest.raises(ModelFailure):
        store.index([updated], models)
    assert store.document("csv") == original
    assert len(store.retrieve(query, "v1")) == 2

    models.fail = False
    stored = store.index([updated], models)
    assert (stored.chunks, stored.embedded) == (1, 1)
    assert [row.chunk_id for row in store.retrieve(query, "v1")] == ["csv:b:0"]
    assert store.document("csv") == updated

    models.digest = "v2"
    assert store.index([updated], models).embedded == 1
    with pytest.raises(IndexUnavailable):
        store.retrieve(query, "v1")
    assert len(store.retrieve(query, "v2")) == 1
