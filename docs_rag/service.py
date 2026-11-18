import re
from typing import Annotated, Literal

import httpx
import ollama
import psycopg
from pydantic import BaseModel, ConfigDict, StringConstraints, ValidationError

from .models import Draft, ModelFailure
from .store import IndexUnavailable, Retrieved

INSUFFICIENT = "Não encontrei evidência suficiente no guia para responder a esta pergunta."
UNAVAILABLE = "A busca está temporariamente indisponível."
DEPENDENCY_ERRORS = (
    psycopg.Error, httpx.HTTPError, ollama.ResponseError, ConnectionError,
    ModelFailure, IndexUnavailable, ValidationError,
)


class AskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class AnswerBlock(BaseModel):
    text: str
    citations: list[int]


class Source(BaseModel):
    number: int
    chunk_id: str
    document_title: str
    section_title: str
    excerpt: str
    url: str


class Answered(BaseModel):
    status: Literal["answered"] = "answered"
    blocks: list[AnswerBlock]
    sources: list[Source]


class InsufficientEvidence(BaseModel):
    status: Literal["insufficient_evidence"] = "insufficient_evidence"
    message: str = INSUFFICIENT


class TemporarilyUnavailable(BaseModel):
    status: Literal["temporarily_unavailable"] = "temporarily_unavailable"
    message: str = UNAVAILABLE
    retryable: Literal[True] = True


def retrieve(question: str, store, models) -> list[Retrieved]:
    digest = models.embedding_digest()
    embedding, = models.embed([question])
    if models.embedding_digest() != digest:
        raise ModelFailure("O modelo de embeddings mudou durante a consulta")
    return store.retrieve(embedding, digest)


def answer(question: str, passages: list[Retrieved], models) -> Answered | InsufficientEvidence:
    draft = models.generate(question, passages)
    return build_answer(draft, passages)


def build_answer(draft: Draft, passages: list[Retrieved]) -> Answered | InsufficientEvidence:
    if draft.status == "insufficient_evidence" and not draft.blocks:
        return InsufficientEvidence()
    if draft.status != "answered" or not draft.blocks:
        raise ModelFailure("Status e blocos incompatíveis")

    sources = {}
    blocks = []
    for block in draft.blocks:
        if re.search(r"\[\d+\]", block.text):
            raise ModelFailure("Citação fora do campo estruturado")
        numbers = []
        for ref in dict.fromkeys(block.refs):
            if not 1 <= ref <= len(passages):
                raise ModelFailure("Citação fora do conjunto recuperado")
            if ref not in sources:
                passage = passages[ref - 1]
                sources[ref] = Source(
                    number=len(sources) + 1, chunk_id=passage.chunk_id,
                    document_title=passage.document_title, section_title=passage.section_title,
                    excerpt=passage.excerpt, url=passage.url,
                )
            numbers.append(sources[ref].number)
        blocks.append(AnswerBlock(text=block.text, citations=numbers))
    return Answered(blocks=blocks, sources=list(sources.values()))
