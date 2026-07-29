from __future__ import annotations
from capabilities.base import CapabilityDeclaration, CapabilityIO, LatencyClass, CostClass
from capabilities.registry import CapabilityRegistry

ollama_generate_decl = CapabilityDeclaration(
    name="ollama_generate",
    description="Generate text using any local Ollama model",
    inputs=[CapabilityIO(name="model", type="string"), CapabilityIO(name="prompt", type="string"),
            CapabilityIO(name="system", type="string", required=False),
            CapabilityIO(name="temperature", type="float", required=False, default=0.7),
            CapabilityIO(name="max_tokens", type="integer", required=False, default=2048)],
    outputs=[CapabilityIO(name="text", type="string"), CapabilityIO(name="model_used", type="string"),
             CapabilityIO(name="tokens_generated", type="integer")],
    latency=LatencyClass.HIGH, offline_support=True, cacheable=False,
    category="local_ai", tags=["ollama", "llm", "generation"],
)

mlx_generate_decl = CapabilityDeclaration(
    name="mlx_generate",
    description="Generate text using MLX models on Apple Silicon",
    inputs=[CapabilityIO(name="model", type="string"), CapabilityIO(name="prompt", type="string"),
            CapabilityIO(name="temperature", type="float", required=False, default=0.7)],
    outputs=[CapabilityIO(name="text", type="string"), CapabilityIO(name="model_used", type="string")],
    latency=LatencyClass.HIGH, offline_support=True, cacheable=False,
    category="local_ai", tags=["mlx", "apple", "llm"],
)

embedding_generate_decl = CapabilityDeclaration(
    name="embedding_generate",
    description="Generate embeddings from text using Sentence Transformers or local models",
    inputs=[CapabilityIO(name="texts", type="list[string]"),
            CapabilityIO(name="model", type="string", required=False, default="all-MiniLM-L6-v2")],
    outputs=[CapabilityIO(name="embeddings", type="list[list[float]]"), CapabilityIO(name="dimension", type="integer")],
    latency=LatencyClass.MEDIUM, offline_support=True, cacheable=True,
    category="local_ai", tags=["embeddings", "sentence-transformers"],
)

local_diffusion_decl = CapabilityDeclaration(
    name="local_diffusion",
    description="Generate images using local diffusion models",
    inputs=[CapabilityIO(name="prompt", type="string"), CapabilityIO(name="negative_prompt", type="string", required=False),
            CapabilityIO(name="width", type="integer", required=False, default=512),
            CapabilityIO(name="height", type="integer", required=False, default=512),
            CapabilityIO(name="num_steps", type="integer", required=False, default=20)],
    outputs=[CapabilityIO(name="path", type="string"), CapabilityIO(name="seed", type="integer")],
    latency=LatencyClass.HIGH, offline_support=True, cacheable=False,
    category="local_ai", tags=["diffusion", "image", "generation"],
)

prompt_route_decl = CapabilityDeclaration(
    name="prompt_route",
    description="Route a prompt to the best model based on task type",
    inputs=[CapabilityIO(name="prompt", type="string"), CapabilityIO(name="task_type", type="string",
            description="reasoning, creative, extraction, summarization, code"),
            CapabilityIO(name="max_tokens", type="integer", required=False, default=2048)],
    outputs=[CapabilityIO(name="text", type="string"), CapabilityIO(name="model_used", type="string"),
             CapabilityIO(name="confidence", type="float")],
    latency=LatencyClass.HIGH, offline_support=True, cacheable=False,
    category="local_ai", tags=["routing", "llm", "prompt"],
)

model_registry_decl = CapabilityDeclaration(
    name="model_registry",
    description="Query and manage the local model registry",
    inputs=[CapabilityIO(name="operation", type="string", description="list, info, load, unload"),
            CapabilityIO(name="model_name", type="string", required=False)],
    outputs=[CapabilityIO(name="models", type="list[dict]"), CapabilityIO(name="total_count", type="integer")],
    latency=LatencyClass.INSTANT, offline_support=True, cacheable=True,
    category="local_ai", tags=["models", "registry", "ollama"],
)

gpu_schedule_decl = CapabilityDeclaration(
    name="gpu_schedule",
    description="Schedule model inference on available GPUs with memory management",
    inputs=[CapabilityIO(name="model", type="string"), CapabilityIO(name="priority", type="integer", required=False, default=5)],
    outputs=[CapabilityIO(name="assigned_device", type="string"), CapabilityIO(name="memory_available", type="integer")],
    latency=LatencyClass.LOW, offline_support=True, cacheable=False,
    category="local_ai", tags=["gpu", "scheduling", "memory"],
)

whisper_transcribe_local_decl = CapabilityDeclaration(
    name="whisper_transcribe_local",
    description="Transcribe audio locally using Whisper",
    inputs=[CapabilityIO(name="path", type="string"),
            CapabilityIO(name="model_size", type="string", required=False, default="base")],
    outputs=[CapabilityIO(name="text", type="string"), CapabilityIO(name="segments", type="list[dict]")],
    latency=LatencyClass.HIGH, offline_support=True, cacheable=True,
    category="local_ai", tags=["whisper", "transcription", "audio"],
)


def register_capabilities(registry: CapabilityRegistry) -> None:
    for decl in [
        ollama_generate_decl, mlx_generate_decl,
        embedding_generate_decl, local_diffusion_decl,
        prompt_route_decl, model_registry_decl,
        gpu_schedule_decl, whisper_transcribe_local_decl,
    ]:
        registry.register(decl)
