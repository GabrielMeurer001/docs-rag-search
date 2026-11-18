import pytest

from docs_rag.markdown import Document, chunks_for, render_markdown


def test_blocks_and_nested_headings_keep_source_metadata():
    markdown = (
        "## Operação {#operacao}\n\n"
        + "x" * 1750
        + "\n\n```sh\n## Dentro do código {#nao-ancora}\n"
        + "echo 'preservado'\n```\n\n### Consultar {#consultar}\n\nGET por ID\n"
    )
    chunks = chunks_for(Document("worker", "Guia", markdown, "origem", "abc"))
    assert [chunk.id for chunk in chunks] == ["worker:operacao:0", "worker:operacao:1", "worker:consultar:0"]
    assert chunks[-1].section_title == "Operação / Consultar"
    assert chunks[1].excerpt == "```sh\n## Dentro do código {#nao-ancora}\necho 'preservado'\n```"
    assert 'id="consultar"' in render_markdown(markdown)


def test_html_and_unsafe_links_are_not_rendered_as_markup():
    html = render_markdown("## Guia {#guia}\n\n<script>foo</script>\n\n[x](javascript:foo)")
    assert "<script>" not in html
    assert 'href="javascript:' not in html


def test_duplicate_anchors_are_rejected():
    with pytest.raises(ValueError, match="Âncora duplicada"):
        render_markdown("## Guia {#guia}\n\nA\n\n## Outro {#guia}\n\nB")
