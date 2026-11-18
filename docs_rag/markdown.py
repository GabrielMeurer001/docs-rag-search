import json
import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from markdown_it import MarkdownIt

SLUG = r"[a-z0-9]+(?:-[a-z0-9]+)*"
HEADING = re.compile(rf"(.+?) +\{{#({SLUG})\}}")
MAX_CHUNK_CHARS = 1800
PARSER = MarkdownIt("commonmark", {"html": False})


@dataclass(frozen=True)
class Document:
    slug: str
    title: str
    markdown: str
    origin: str
    revision: str


@dataclass(frozen=True)
class Chunk:
    id: str
    section_title: str
    anchor: str
    position: int
    excerpt: str
    embedding_text: str

    @property
    def content_hash(self):
        return sha256(self.embedding_text.encode()).hexdigest()


def load_documents(manifest: Path) -> list[Document]:
    documents = []
    seen = set()
    root = manifest.parent.resolve()
    for entry in json.loads(manifest.read_text(encoding="utf-8")):
        path = (root / entry["file"]).resolve()
        slug = entry["slug"]
        if not path.is_relative_to(root) or path.suffix != ".md":
            raise ValueError(f"Markdown fora do diretório do corpus: {path}")
        if not re.fullmatch(SLUG, slug) or slug in seen:
            raise ValueError(f"Slug inválido ou duplicado: {slug}")
        seen.add(slug)
        documents.append(Document(
            slug, entry["title"], path.read_text(encoding="utf-8"),
            entry["origin"], entry["revision"],
        ))
    if not documents:
        raise ValueError("O manifesto do corpus está vazio")
    return documents


def parse_document(markdown: str):
    tokens = PARSER.parse(markdown)
    sections = []
    ancestors = []
    anchors = set()
    for index, token in enumerate(tokens):
        if token.type != "heading_open" or token.level != 0:
            continue
        inline = tokens[index + 1]
        match = HEADING.fullmatch(inline.content)
        if not match:
            raise ValueError(f"Título sem âncora explícita: {inline.content}")
        title, anchor = match.groups()
        if anchor in anchors:
            raise ValueError(f"Âncora duplicada: {anchor}")
        anchors.add(anchor)
        token.attrSet("id", anchor)
        inline.content = title
        inline.children = PARSER.parseInline(title)[0].children
        level = int(token.tag[1:])
        while ancestors and ancestors[-1][0] >= level:
            ancestors.pop()
        ancestors.append((level, title))
        sections.append((index, anchor, " / ".join(text for _, text in ancestors)))
    return tokens, sections


def chunks_for(document: Document) -> list[Chunk]:
    tokens, sections = parse_document(document.markdown)
    if not sections or sections[0][0] != 0:
        raise ValueError(f"O documento deve começar por uma seção: {document.slug}")
    lines = document.markdown.splitlines()
    chunks = []
    for section_index, (start, anchor, title) in enumerate(sections):
        stop = sections[section_index + 1][0] if section_index + 1 < len(sections) else len(tokens)
        blocks = [
            "\n".join(lines[token.map[0]:token.map[1]]).strip()
            for token in tokens[start + 3:stop] if token.level == 0 and token.map
        ]
        excerpts = []
        for block in blocks:
            if len(block) > MAX_CHUNK_CHARS:
                raise ValueError(f"Bloco Markdown longo demais em {document.slug}#{anchor}")
            if excerpts and len(excerpts[-1]) + len(block) + 2 <= MAX_CHUNK_CHARS:
                excerpts[-1] += "\n\n" + block
            else:
                excerpts.append(block)
        for position, excerpt in enumerate(excerpts):
            chunks.append(Chunk(
                f"{document.slug}:{anchor}:{position}", title, anchor, position,
                excerpt, f"{document.title}\n{title}\n\n{excerpt}",
            ))
    if not chunks:
        raise ValueError(f"O documento não contém trechos: {document.slug}")
    return chunks


def render_markdown(markdown: str) -> str:
    tokens, _ = parse_document(markdown)
    return PARSER.renderer.render(tokens, PARSER.options, {})
