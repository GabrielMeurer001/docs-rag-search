import logging
from html import escape
from time import perf_counter

import psycopg
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import ROOT, Settings
from .markdown import render_markdown
from .models import LocalModels
from .service import (
    DEPENDENCY_ERRORS, Answered, AskRequest, InsufficientEvidence, TemporarilyUnavailable, answer, retrieve,
)
from .store import Store

log = logging.getLogger("uvicorn.error.docs_rag")
DIST = ROOT / "frontend" / "dist"
PUBLIC = ROOT / "frontend" / "public"


def create_app(store=None, models=None):
    settings = Settings.from_env()
    store = Store(settings.database_url) if store is None else store
    models = LocalModels(settings) if models is None else models
    app = FastAPI(title="docs-rag-search")

    @app.post("/api/ask", responses={503: {"model": TemporarilyUnavailable}})
    def ask(request: AskRequest) -> Answered | InsufficientEvidence:
        started = perf_counter()
        try:
            passages = retrieve(request.question, store, models)
            result = answer(request.question, passages, models)
        except DEPENDENCY_ERRORS as exc:
            log.warning("Busca indisponível: %s", exc.__class__.__name__)
            return JSONResponse(status_code=503, content=TemporarilyUnavailable().model_dump())
        log.info("Busca concluída: status=%s tempo_ms=%.0f", result.status, (perf_counter() - started) * 1000)
        return result

    @app.get("/guia/{slug}", response_class=HTMLResponse, include_in_schema=False)
    def guide(slug: str):
        try:
            document = store.document(slug)
        except psycopg.Error as exc:
            raise HTTPException(503, "Guia temporariamente indisponível") from exc
        if document is None:
            raise HTTPException(404, "Guia não encontrado")
        title = escape(document.title)
        origin = escape(document.origin)
        revision = escape(document.revision)
        content = render_markdown(document.markdown)
        return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <link rel="stylesheet" href="/guide.css">
</head>
<body>
  <main>
    <a href="/">← Voltar à busca</a>
    <article>
      <h1>{title}</h1>
      <p class="origin">{origin} · revisão <code>{revision}</code></p>
      {content}
    </article>
  </main>
</body>
</html>"""

    @app.get("/guide.css", include_in_schema=False)
    def guide_styles():
        return FileResponse(PUBLIC / "guide.css", media_type="text/css")

    @app.get("/", include_in_schema=False)
    def home():
        if not (DIST / "index.html").is_file():
            return HTMLResponse("Compile a interface com npm run build na pasta frontend.", status_code=503)
        return FileResponse(DIST / "index.html")

    app.mount("/assets", StaticFiles(directory=DIST / "assets", check_dir=False), name="assets")
    return app


app = create_app()
