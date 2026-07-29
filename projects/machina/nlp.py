from __future__ import annotations
from capabilities.base import CapabilityDeclaration, CapabilityIO, LatencyClass, CostClass
from capabilities.registry import CapabilityRegistry

extract_entities_decl = CapabilityDeclaration(
    name="extract_entities",
    description="Extract named entities from text using spaCy",
    inputs=[CapabilityIO(name="text", type="string"), CapabilityIO(name="model", type="string", required=False, default="en_core_web_sm")],
    outputs=[CapabilityIO(name="entities", type="list[dict]"), CapabilityIO(name="entity_types", type="list[str]")],
    latency=LatencyClass.MEDIUM, offline_support=True, cacheable=True, deterministic=True,
    category="nlp", tags=["spacy", "ner", "entities"],
)

extract_keywords_decl = CapabilityDeclaration(
    name="extract_keywords",
    description="Extract key phrases and keywords from text using RAKE/TF-IDF",
    inputs=[CapabilityIO(name="text", type="string"), CapabilityIO(name="method", type="string", required=False, default="rake"),
            CapabilityIO(name="max_keywords", type="integer", required=False, default=20)],
    outputs=[CapabilityIO(name="keywords", type="list[dict]")],
    latency=LatencyClass.LOW, offline_support=True, cacheable=True, deterministic=True,
    category="nlp", tags=["keywords", "extraction"],
)

summarize_text_decl = CapabilityDeclaration(
    name="summarize_text",
    description="Summarize text using extractive or abstractive methods",
    inputs=[CapabilityIO(name="text", type="string"),
            CapabilityIO(name="max_sentences", type="integer", required=False, default=5),
            CapabilityIO(name="method", type="string", required=False, default="extractive")],
    outputs=[CapabilityIO(name="summary", type="string"), CapabilityIO(name="compression_ratio", type="float")],
    latency=LatencyClass.MEDIUM, offline_support=True, cacheable=True,
    category="nlp", tags=["summarization", "text"],
)

language_detect_decl = CapabilityDeclaration(
    name="language_detect",
    description="Detect the language of a text",
    inputs=[CapabilityIO(name="text", type="string")],
    outputs=[CapabilityIO(name="language", type="string"), CapabilityIO(name="confidence", type="float"),
             CapabilityIO(name="all_scores", type="dict")],
    latency=LatencyClass.INSTANT, offline_support=True, cacheable=True, deterministic=True,
    category="nlp", tags=["language", "detection"],
)

generate_embeddings_decl = CapabilityDeclaration(
    name="generate_embeddings",
    description="Generate text embeddings using Sentence Transformers",
    inputs=[CapabilityIO(name="texts", type="list[string]"),
            CapabilityIO(name="model", type="string", required=False, default="all-MiniLM-L6-v2")],
    outputs=[CapabilityIO(name="embeddings", type="list[list[float]]"), CapabilityIO(name="dimension", type="integer")],
    latency=LatencyClass.MEDIUM, offline_support=True, cacheable=True,
    category="nlp", tags=["embeddings", "transformers"],
)

vector_search_decl = CapabilityDeclaration(
    name="vector_search",
    description="Search vectors using FAISS or LanceDB for similarity search",
    inputs=[CapabilityIO(name="query_vector", type="list[float]"),
            CapabilityIO(name="vectors", type="list[list[float]]"),
            CapabilityIO(name="k", type="integer", required=False, default=10)],
    outputs=[CapabilityIO(name="indices", type="list[int]"), CapabilityIO(name="scores", type="list[float]"),
             CapabilityIO(name="results", type="list[dict]")],
    latency=LatencyClass.MEDIUM, offline_support=True, cacheable=False,
    category="nlp", tags=["vector", "search", "faiss", "lancedb"],
)

tokenize_text_decl = CapabilityDeclaration(
    name="tokenize_text",
    description="Tokenize text into words, sentences, or subword tokens",
    inputs=[CapabilityIO(name="text", type="string"),
            CapabilityIO(name="level", type="string", required=False, default="words")],
    outputs=[CapabilityIO(name="tokens", type="list[str]"), CapabilityIO(name="count", type="integer")],
    latency=LatencyClass.INSTANT, offline_support=True, cacheable=True, deterministic=True,
    category="nlp", tags=["tokenization", "nlp"],
)

coreference_resolve_decl = CapabilityDeclaration(
    name="coreference_resolve",
    description="Resolve coreference chains in text (pronouns to entities)",
    inputs=[CapabilityIO(name="text", type="string")],
    outputs=[CapabilityIO(name="chains", type="list[list[dict]]"), CapabilityIO(name="resolved_text", type="string")],
    latency=LatencyClass.HIGH, offline_support=True, cacheable=True,
    category="nlp", tags=["coreference", "resolution"],
)

relation_extraction_decl = CapabilityDeclaration(
    name="relation_extraction",
    description="Extract semantic relations between entities in text",
    inputs=[CapabilityIO(name="text", type="string")],
    outputs=[CapabilityIO(name="relations", type="list[dict]")],
    latency=LatencyClass.HIGH, offline_support=True, cacheable=True,
    category="nlp", tags=["relations", "extraction"],
)

topic_model_decl = CapabilityDeclaration(
    name="topic_model",
    description="Identify topics in a collection of documents",
    inputs=[CapabilityIO(name="documents", type="list[string]"),
            CapabilityIO(name="num_topics", type="integer", required=False, default=5)],
    outputs=[CapabilityIO(name="topics", type="list[dict]"), CapabilityIO(name="document_assignments", type="list[int]")],
    latency=LatencyClass.HIGH, offline_support=True, cacheable=True,
    category="nlp", tags=["topic", "modelling", "lda"],
)


def register_capabilities(registry: CapabilityRegistry) -> None:
    for decl in [
        extract_entities_decl, extract_keywords_decl, summarize_text_decl,
        language_detect_decl, generate_embeddings_decl, vector_search_decl,
        tokenize_text_decl, coreference_resolve_decl, relation_extraction_decl,
        topic_model_decl,
    ]:
        registry.register(decl)
