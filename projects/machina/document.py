from __future__ import annotations
from capabilities.base import (
    CapabilityDeclaration, CapabilityIO, LatencyClass, CostClass,
)
from capabilities.registry import CapabilityRegistry

parse_pdf_decl = CapabilityDeclaration(
    name="parse_pdf",
    description="Extract text and metadata from PDF documents",
    inputs=[CapabilityIO(name="path", type="string", description="File path or URL"),
            CapabilityIO(name="extract_tables", type="boolean", required=False, default=False)],
    outputs=[CapabilityIO(name="text", type="string"), CapabilityIO(name="metadata", type="dict"),
             CapabilityIO(name="pages", type="integer"), CapabilityIO(name="tables", type="list")],
    latency=LatencyClass.MEDIUM, offline_support=True, cacheable=True,
    category="document", tags=["pdf", "document"],
)

parse_docx_decl = CapabilityDeclaration(
    name="parse_docx",
    description="Extract text and metadata from DOCX documents",
    inputs=[CapabilityIO(name="path", type="string")],
    outputs=[CapabilityIO(name="text", type="string"), CapabilityIO(name="metadata", type="dict")],
    latency=LatencyClass.LOW, offline_support=True, cacheable=True,
    category="document", tags=["docx", "word"],
)

parse_pptx_decl = CapabilityDeclaration(
    name="parse_pptx",
    description="Extract text from PPTX presentations",
    inputs=[CapabilityIO(name="path", type="string")],
    outputs=[CapabilityIO(name="slides", type="list[dict]"), CapabilityIO(name="metadata", type="dict")],
    latency=LatencyClass.LOW, offline_support=True, cacheable=True,
    category="document", tags=["pptx", "presentation"],
)

parse_markdown_decl = CapabilityDeclaration(
    name="parse_markdown",
    description="Parse Markdown content into structured sections",
    inputs=[CapabilityIO(name="markdown", type="string")],
    outputs=[CapabilityIO(name="sections", type="list[dict]"), CapabilityIO(name="headings", type="list[str]"),
             CapabilityIO(name="code_blocks", type="list[dict]"), CapabilityIO(name="tables", type="list")],
    latency=LatencyClass.INSTANT, offline_support=True, cacheable=True, deterministic=True,
    category="document", tags=["markdown", "parse"],
)

parse_html_doc_decl = CapabilityDeclaration(
    name="parse_html_doc",
    description="Parse HTML document into readable text with structure",
    inputs=[CapabilityIO(name="html", type="string")],
    outputs=[CapabilityIO(name="text", type="string"), CapabilityIO(name="title", type="string"),
             CapabilityIO(name="meta_tags", type="dict")],
    latency=LatencyClass.LOW, offline_support=True, cacheable=True, deterministic=True,
    category="document", tags=["html", "parse"],
)

parse_csv_decl = CapabilityDeclaration(
    name="parse_csv",
    description="Parse CSV data into structured rows",
    inputs=[CapabilityIO(name="path", type="string"), CapabilityIO(name="delimiter", type="string", required=False, default=","),
            CapabilityIO(name="has_header", type="boolean", required=False, default=True)],
    outputs=[CapabilityIO(name="columns", type="list[str]"), CapabilityIO(name="rows", type="list[list]"),
             CapabilityIO(name="row_count", type="integer")],
    latency=LatencyClass.LOW, offline_support=True, cacheable=True, deterministic=True,
    category="document", tags=["csv", "tabular"],
)

parse_json_decl = CapabilityDeclaration(
    name="parse_json",
    description="Parse JSON data with validation",
    inputs=[CapabilityIO(name="data", type="string"), CapabilityIO(name="schema", type="dict", required=False)],
    outputs=[CapabilityIO(name="parsed", type="any"), CapabilityIO(name="valid", type="boolean"),
             CapabilityIO(name="errors", type="list[str]")],
    latency=LatencyClass.INSTANT, offline_support=True, cacheable=True, deterministic=True,
    category="document", tags=["json", "parse"],
)

parse_yaml_decl = CapabilityDeclaration(
    name="parse_yaml",
    description="Parse YAML data into Python objects",
    inputs=[CapabilityIO(name="data", type="string")],
    outputs=[CapabilityIO(name="parsed", type="dict")],
    latency=LatencyClass.INSTANT, offline_support=True, cacheable=True, deterministic=True,
    category="document", tags=["yaml", "parse"],
)

parse_xml_decl = CapabilityDeclaration(
    name="parse_xml",
    description="Parse XML documents into structured trees",
    inputs=[CapabilityIO(name="data", type="string")],
    outputs=[CapabilityIO(name="tree", type="dict"), CapabilityIO(name="root", type="string")],
    latency=LatencyClass.LOW, offline_support=True, cacheable=True, deterministic=True,
    category="document", tags=["xml", "parse"],
)

parse_epub_decl = CapabilityDeclaration(
    name="parse_epub",
    description="Extract text and metadata from EPUB ebooks",
    inputs=[CapabilityIO(name="path", type="string")],
    outputs=[CapabilityIO(name="text", type="string"), CapabilityIO(name="metadata", type="dict"),
             CapabilityIO(name="chapters", type="list[dict]")],
    latency=LatencyClass.MEDIUM, offline_support=True, cacheable=True,
    category="document", tags=["epub", "ebook"],
)

parse_latex_decl = CapabilityDeclaration(
    name="parse_latex",
    description="Parse LaTeX documents and extract text, equations, and structure",
    inputs=[CapabilityIO(name="latex", type="string")],
    outputs=[CapabilityIO(name="text", type="string"), CapabilityIO(name="equations", type="list[str]"),
             CapabilityIO(name="sections", type="list[dict]"), CapabilityIO(name="citations", type="list[str]")],
    latency=LatencyClass.MEDIUM, offline_support=True, cacheable=True,
    category="document", tags=["latex", "academic"],
)

ocr_extract_decl = CapabilityDeclaration(
    name="ocr_extract",
    description="Extract text from images using Tesseract OCR",
    inputs=[CapabilityIO(name="image_path", type="string"), CapabilityIO(name="language", type="string", required=False, default="eng")],
    outputs=[CapabilityIO(name="text", type="string"), CapabilityIO(name="confidence", type="float"),
             CapabilityIO(name="words", type="list[dict]")],
    latency=LatencyClass.HIGH, offline_support=True, cacheable=True,
    category="document", tags=["ocr", "image", "text"],
)

extract_tables_decl = CapabilityDeclaration(
    name="extract_tables",
    description="Extract tabular data from documents (PDF, HTML, images)",
    inputs=[CapabilityIO(name="path", type="string"), CapabilityIO(name="source_type", type="string", required=False)],
    outputs=[CapabilityIO(name="tables", type="list[list[list]]"), CapabilityIO(name="page_numbers", type="list[int]")],
    latency=LatencyClass.MEDIUM, offline_support=True, cacheable=True,
    category="document", tags=["tables", "extraction"],
)

extract_citations_decl = CapabilityDeclaration(
    name="extract_citations",
    description="Extract citation references from academic text",
    inputs=[CapabilityIO(name="text", type="string"), CapabilityIO(name="format", type="string", required=False, default="auto")],
    outputs=[CapabilityIO(name="citations", type="list[dict]"), CapabilityIO(name="format_detected", type="string")],
    latency=LatencyClass.MEDIUM, offline_support=True, cacheable=True,
    category="document", tags=["citations", "academic", "references"],
)

reference_parse_decl = CapabilityDeclaration(
    name="reference_parse",
    description="Parse bibliographic references from text",
    inputs=[CapabilityIO(name="reference_string", type="string")],
    outputs=[CapabilityIO(name="parsed", type="dict"), CapabilityIO(name="confidence", type="float")],
    latency=LatencyClass.MEDIUM, offline_support=True, cacheable=True,
    category="document", tags=["references", "bibliography"],
)


def register_capabilities(registry: CapabilityRegistry) -> None:
    for decl in [
        parse_pdf_decl, parse_docx_decl, parse_pptx_decl,
        parse_markdown_decl, parse_html_doc_decl,
        parse_csv_decl, parse_json_decl, parse_yaml_decl, parse_xml_decl,
        parse_epub_decl, parse_latex_decl,
        ocr_extract_decl,
        extract_tables_decl, extract_citations_decl, reference_parse_decl,
    ]:
        registry.register(decl)
