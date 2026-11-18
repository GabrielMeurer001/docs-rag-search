from dataclasses import dataclass
from os import getenv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIMENSIONS = 1024


@dataclass(frozen=True)
class Settings:
    database_url: str = "postgresql://docs_rag:docs-rag-local@127.0.0.1:25433/docs_rag"
    ollama_url: str = "http://127.0.0.1:11434"
    embedding_model: str = "bge-m3:latest"
    answer_model: str = "qwen3.5:4b"

    @classmethod
    def from_env(cls):
        return cls(
            database_url=getenv("DOCS_RAG_DATABASE_URL", cls.database_url),
            ollama_url=getenv("DOCS_RAG_OLLAMA_URL", cls.ollama_url),
            embedding_model=getenv("DOCS_RAG_EMBEDDING_MODEL", cls.embedding_model),
            answer_model=getenv("DOCS_RAG_ANSWER_MODEL", cls.answer_model),
        )
