import httpx
import pytest
from fastapi.testclient import TestClient

from docs_rag.app import create_app
from docs_rag.markdown import Document
from docs_rag.models import Draft
from docs_rag.store import IndexUnavailable, Retrieved

PASSAGES = [
    Retrieved("csv:formato:0", "csv", "Manual", "Formato", "formato", "CSV UTF-8"),
    Retrieved("csv:envio:0", "csv", "Manual", "Envio", "envio", "POST /reports"),
]


class FakeStore:
    def retrieve(self, vector, digest):
        assert vector == [1.0] and digest == "digest"
        return PASSAGES

    def document(self, slug):
        if slug == "csv":
            return Document("csv", "Manual", "## Envio {#envio}\n\nPOST /reports", "worker", "abc")
        return None


class FakeModels:
    def __init__(self, draft=None, error=None):
        self.draft = draft
        self.error = error

    def embedding_digest(self):
        return "digest"

    def embed(self, texts):
        assert texts == ["Como envio?"]
        return [[1.0]]

    def generate(self, question, passages):
        assert question == "Como envio?" and passages == PASSAGES
        if self.error:
            raise self.error
        return Draft.model_validate(self.draft)


def ask(client):
    return client.post("/api/ask", json={"question": "  Como envio?  "})


def test_numbering_and_source_metadata_are_from_retrieval():
    client = TestClient(create_app(FakeStore(), FakeModels({
        "status": "answered",
        "blocks": [
            {"text": "Faça POST.", "refs": [2, 2]},
            {"text": "O arquivo usa UTF-8.", "refs": [2, 1]},
        ],
    })))
    response = ask(client)
    assert response.status_code == 200
    body = response.json()
    assert body["blocks"] == [
        {"text": "Faça POST.", "citations": [1]},
        {"text": "O arquivo usa UTF-8.", "citations": [1, 2]},
    ]
    assert body["sources"][0] == {
        "number": 1, "chunk_id": "csv:envio:0", "document_title": "Manual",
        "section_title": "Envio", "excerpt": "POST /reports", "url": "/guia/csv#envio",
    }
    assert body["sources"][1]["url"] == "/guia/csv#formato"
    assert 'id="envio"' in client.get("/guia/csv").text
    assert client.get("/guia/desconhecido").status_code == 404


def test_insufficient_evidence():
    client = TestClient(create_app(FakeStore(), FakeModels({"status": "insufficient_evidence", "blocks": []})))
    response = ask(client)
    assert response.status_code == 200
    assert response.json()["status"] == "insufficient_evidence"
    assert "sources" not in response.json()


@pytest.mark.parametrize("draft", [
    {"status": "answered", "blocks": [{"text": "Texto.", "refs": [3]}]},
    {"status": "answered", "blocks": [{"text": "Texto.", "refs": []}]},
    {"status": "answered", "blocks": [{"text": "Texto.", "refs": ["1"]}]},
    {"status": "answered", "blocks": [{"text": "Texto. [42]", "refs": [1]}]},
    {"status": "answered", "blocks": []},
    {"status": "insufficient_evidence", "blocks": [{"text": "Texto.", "refs": [1]}]},
])
def test_invalid_draft_is_recoverable(draft):
    client = TestClient(create_app(FakeStore(), FakeModels(draft)))
    response = ask(client)
    assert response.status_code == 503
    assert response.json() == {
        "status": "temporarily_unavailable",
        "message": "A busca está temporariamente indisponível.",
        "retryable": True,
    }


def test_model_timeout_can_be_retried():
    models = FakeModels({"status": "insufficient_evidence", "blocks": []}, httpx.ReadTimeout("deadline"))
    client = TestClient(create_app(FakeStore(), models))
    assert ask(client).status_code == 503
    models.error = None
    assert ask(client).status_code == 200


def test_unavailable_index_is_recoverable():
    class EmptyStore(FakeStore):
        def retrieve(self, vector, digest):
            raise IndexUnavailable("not indexed")

    response = ask(TestClient(create_app(EmptyStore(), FakeModels())))
    assert response.status_code == 503
    assert response.json()["retryable"] is True


@pytest.mark.parametrize("body", [{"question": "  "}, {"question": "x" * 501}, {"question": 123}, {}])
def test_invalid_questions_return_422(body):
    client = TestClient(create_app(FakeStore(), FakeModels()))
    assert client.post("/api/ask", json=body).status_code == 422
