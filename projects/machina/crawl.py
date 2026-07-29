from __future__ import annotations
from capabilities.base import (
    CapabilityDeclaration, CapabilityIO, LatencyClass, CostClass, RetryPolicy,
)
from capabilities.registry import CapabilityRegistry

fetch_url_decl = CapabilityDeclaration(
    name="fetch_url",
    description="Fetch a URL and return raw HTML content",
    inputs=[CapabilityIO(name="url", type="string", description="URL to fetch"),
            CapabilityIO(name="timeout", type="integer", required=False, default=30)],
    outputs=[CapabilityIO(name="content", type="string"), CapabilityIO(name="status_code", type="integer"),
             CapabilityIO(name="headers", type="dict")],
    latency=LatencyClass.MEDIUM, internet_required=True, cacheable=True,
    category="crawl", tags=["http", "fetch"],
)

scrape_url_decl = CapabilityDeclaration(
    name="scrape_url",
    description="Fetch and parse a URL into structured content using Trafilatura/Readability",
    inputs=[CapabilityIO(name="url", type="string"),
            CapabilityIO(name="extract_metadata", type="boolean", required=False, default=True)],
    outputs=[CapabilityIO(name="title", type="string"), CapabilityIO(name="body", type="string"),
             CapabilityIO(name="metadata", type="dict")],
    latency=LatencyClass.MEDIUM, internet_required=True, cacheable=True,
    category="crawl", tags=["scraping", "content"],
)

parse_html_decl = CapabilityDeclaration(
    name="parse_html",
    description="Parse HTML content and extract structured data using BeautifulSoup",
    inputs=[CapabilityIO(name="html", type="string"),
            CapabilityIO(name="extract_tables", type="boolean", required=False, default=False)],
    outputs=[CapabilityIO(name="body_text", type="string"), CapabilityIO(name="tables", type="list"),
             CapabilityIO(name="links", type="list[dict]"), CapabilityIO(name="images", type="list[str]")],
    latency=LatencyClass.LOW, internet_required=False, cacheable=True,
    category="crawl", tags=["html", "parse", "beautifulsoup"],
)

sitemap_discover_decl = CapabilityDeclaration(
    name="sitemap_discover",
    description="Discover and parse sitemap.xml for a domain",
    inputs=[CapabilityIO(name="domain", type="string")],
    outputs=[CapabilityIO(name="urls", type="list[str]"), CapabilityIO(name="sitemap_type", type="string")],
    latency=LatencyClass.HIGH, internet_required=True, cacheable=True,
    category="crawl", tags=["sitemap", "discovery"],
)

recursive_crawl_decl = CapabilityDeclaration(
    name="recursive_crawl",
    description="Recursively crawl a website up to a depth limit",
    inputs=[CapabilityIO(name="start_url", type="string"),
            CapabilityIO(name="max_depth", type="integer", required=False, default=2),
            CapabilityIO(name="max_pages", type="integer", required=False, default=50),
            CapabilityIO(name="allowed_domains", type="list[string]", required=False)],
    outputs=[CapabilityIO(name="pages", type="list[dict]"), CapabilityIO(name="crawl_stats", type="dict")],
    latency=LatencyClass.HIGH, internet_required=True, cacheable=False,
    category="crawl", tags=["crawl", "recursive"],
)

robots_parse_decl = CapabilityDeclaration(
    name="robots_parse",
    description="Parse a robots.txt file for crawl rules",
    inputs=[CapabilityIO(name="url", type="string")],
    outputs=[CapabilityIO(name="rules", type="dict"), CapabilityIO(name="sitemaps", type="list[str]")],
    latency=LatencyClass.LOW, internet_required=True, cacheable=True,
    category="crawl", tags=["robots", "crawl_rules"],
)

url_canonicalize_decl = CapabilityDeclaration(
    name="url_canonicalize",
    description="Canonicalize and normalize URLs",
    inputs=[CapabilityIO(name="url", type="string")],
    outputs=[CapabilityIO(name="canonical_url", type="string"), CapabilityIO(name="normalized", type="string")],
    latency=LatencyClass.INSTANT, internet_required=False, cacheable=True,
    deterministic=True,
    category="crawl", tags=["url", "canonical"],
)

duplicate_detect_decl = CapabilityDeclaration(
    name="duplicate_detect",
    description="Detect near-duplicate content using simhash or MinHash",
    inputs=[CapabilityIO(name="contents", type="list[string]", description="List of text contents to compare")],
    outputs=[CapabilityIO(name="duplicates", type="list[tuple]"), CapabilityIO(name="similarity_matrix", type="list[list]")],
    latency=LatencyClass.MEDIUM, internet_required=False, cacheable=True,
    category="crawl", tags=["dedup", "similarity"],
)


def register_capabilities(registry: CapabilityRegistry) -> None:
    for decl in [
        fetch_url_decl, scrape_url_decl, parse_html_decl,
        sitemap_discover_decl, recursive_crawl_decl, robots_parse_decl,
        url_canonicalize_decl, duplicate_detect_decl,
    ]:
        registry.register(decl)
