from app.renderers.json_renderer import JSONRenderer
from app.renderers.markdown_renderer import MarkdownRenderer
from app.schemas.canonical import CanonicalAsset, CanonicalBlock, CanonicalField, CanonicalModel


def _canonical(*, fields=None, blocks=None, assets=None) -> CanonicalModel:
    return CanonicalModel(
        canonical_version="1.0",
        task_id="task_renderer",
        doc_id="doc_renderer",
        schema_id="schema_renderer",
        doc_meta={"source_name": "input.json"},
        fields=fields or {},
        blocks=blocks or [],
        assets=assets or [],
    )


def _field(value) -> CanonicalField:
    return CanonicalField(value=value, type="string")


def test_json_renderer_prefers_explicit_summary_and_keyword_list():
    canonical = _canonical(
        fields={
            "summary": _field("Explicit"),
            "keywords": _field(["one", 2]),
            "empty": _field(None),
        }
    )
    rendered = JSONRenderer().render(canonical, schema_version="2.0.0")

    assert rendered.metadata.document_summary == "Explicit"
    assert rendered.metadata.keywords == ["one", "2"]
    assert rendered.schema_ref.version == "2.0.0"
    assert "empty" not in rendered.data


def test_json_renderer_uses_scalar_keywords_and_field_fallbacks():
    scalar = JSONRenderer().render(_canonical(fields={"keywords": _field("single")}))
    assert scalar.metadata.keywords == ["single"]

    fallback = JSONRenderer().render(
        _canonical(
            fields={
                "title": _field("Same"),
                "publish_org": _field("Same"),
                "author": _field("Author"),
                "doc_type": _field("Policy"),
            }
        )
    )
    assert fallback.metadata.keywords == ["Same", "Author", "Policy"]


def test_json_renderer_summary_falls_back_to_paragraph_then_any_block():
    paragraph = _canonical(
        blocks=[CanonicalBlock(block_id="p", type="paragraph", text=" Body ", source_blocks=["p"])]
    )
    assert JSONRenderer().render(paragraph).metadata.document_summary == "Body"

    heading = _canonical(
        blocks=[CanonicalBlock(block_id="h", type="heading", text=" Heading ", source_blocks=["h"])]
    )
    assert JSONRenderer().render(heading).metadata.document_summary == "Heading"
    assert JSONRenderer().render(_canonical()).metadata.document_summary is None


def test_markdown_renderer_covers_title_heading_table_empty_and_asset():
    canonical = _canonical(
        fields={"title": _field("Document")},
        blocks=[
            CanonicalBlock(block_id="h", type="heading", level=9, text="Deep", source_blocks=["h"]),
            CanonicalBlock(block_id="t", type="table", text="a | b", source_blocks=["t"]),
            CanonicalBlock(block_id="e", type="paragraph", text="", source_blocks=[]),
        ],
        assets=[
            CanonicalAsset(asset_id="asset_1", type="image", path="assets/image.png")
        ],
    )

    markdown = MarkdownRenderer().render(canonical)

    assert "title: Document" in markdown
    assert "###### Deep" in markdown
    assert "a | b" in markdown
    assert "<!-- block_id: e | source_blocks:  -->" in markdown
    assert "![asset_1](assets/image.png)" in markdown


def test_markdown_renderer_uses_first_heading_or_no_title():
    heading = _canonical(
        blocks=[CanonicalBlock(block_id="h", type="heading", text="Fallback", source_blocks=["h"])]
    )
    assert "title: Fallback" in MarkdownRenderer().render(heading)

    paragraph = _canonical(
        blocks=[CanonicalBlock(block_id="p", type="paragraph", text="Body", source_blocks=["p"])]
    )
    markdown = MarkdownRenderer().render(paragraph)
    assert "title:" not in markdown
    assert MarkdownRenderer._render_table("") == ""
