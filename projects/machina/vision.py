from __future__ import annotations
from capabilities.base import CapabilityDeclaration, CapabilityIO, LatencyClass, CostClass
from capabilities.registry import CapabilityRegistry

image_analyze_decl = CapabilityDeclaration(
    name="image_analyze",
    description="Analyze image content using OpenCV: detect edges, contours, colors, faces",
    inputs=[CapabilityIO(name="path", type="string"), CapabilityIO(name="analysis", type="string", required=False)],
    outputs=[CapabilityIO(name="features", type="dict"), CapabilityIO(name="metadata", type="dict")],
    latency=LatencyClass.MEDIUM, offline_support=True, cacheable=True,
    category="vision", tags=["opencv", "image", "analysis"],
)

process_image_decl = CapabilityDeclaration(
    name="process_image",
    description="Apply image processing operations using Pillow (resize, crop, filter, convert)",
    inputs=[CapabilityIO(name="path", type="string"), CapabilityIO(name="operation", type="string"),
            CapabilityIO(name="params", type="dict", required=False)],
    outputs=[CapabilityIO(name="path", type="string"), CapabilityIO(name="metadata", type="dict")],
    latency=LatencyClass.LOW, offline_support=True, cacheable=False,
    category="vision", tags=["pillow", "image", "processing"],
)

ocr_image_decl = CapabilityDeclaration(
    name="ocr_image",
    description="Extract text from images using EasyOCR or Tesseract",
    inputs=[CapabilityIO(name="path", type="string"), CapabilityIO(name="languages", type="list[string]", required=False)],
    outputs=[CapabilityIO(name="text", type="string"), CapabilityIO(name="boxes", type="list[dict]")],
    latency=LatencyClass.MEDIUM, offline_support=True, cacheable=True,
    category="vision", tags=["ocr", "tesseract", "easyocr"],
)

clip_analyze_decl = CapabilityDeclaration(
    name="clip_analyze",
    description="Analyze images using CLIP: zero-shot classification, similarity, captioning",
    inputs=[CapabilityIO(name="path", type="string"),
            CapabilityIO(name="candidates", type="list[string]", required=False)],
    outputs=[CapabilityIO(name="scores", type="dict"), CapabilityIO(name="embedding", type="list[float]")],
    latency=LatencyClass.HIGH, offline_support=True, cacheable=True,
    category="vision", tags=["clip", "vision", "embedding"],
)

segment_image_decl = CapabilityDeclaration(
    name="segment_image",
    description="Segment objects in images using SAM (Segment Anything)",
    inputs=[CapabilityIO(name="path", type="string"),
            CapabilityIO(name="points", type="list[dict]", required=False)],
    outputs=[CapabilityIO(name="masks", type="list"), CapabilityIO(name="scores", type="list[float]")],
    latency=LatencyClass.HIGH, offline_support=True, cacheable=False,
    category="vision", tags=["sam", "segmentation"],
)

detect_objects_decl = CapabilityDeclaration(
    name="detect_objects",
    description="Detect objects in images using YOLO",
    inputs=[CapabilityIO(name="path", type="string"),
            CapabilityIO(name="confidence", type="float", required=False, default=0.5)],
    outputs=[CapabilityIO(name="objects", type="list[dict]"), CapabilityIO(name="count", type="integer")],
    latency=LatencyClass.HIGH, offline_support=True, cacheable=False,
    category="vision", tags=["yolo", "detection", "objects"],
)

image_similarity_decl = CapabilityDeclaration(
    name="image_similarity",
    description="Compute similarity between two images",
    inputs=[CapabilityIO(name="path_a", type="string"), CapabilityIO(name="path_b", type="string"),
            CapabilityIO(name="method", type="string", required=False, default="structural_similarity")],
    outputs=[CapabilityIO(name="similarity", type="float"), CapabilityIO(name="method", type="string")],
    latency=LatencyClass.LOW, offline_support=True, cacheable=True, deterministic=True,
    category="vision", tags=["similarity", "compare"],
)

color_analysis_decl = CapabilityDeclaration(
    name="color_analysis",
    description="Extract color palette and analyze color distribution in images",
    inputs=[CapabilityIO(name="path", type="string"), CapabilityIO(name="num_colors", type="integer", required=False, default=10)],
    outputs=[CapabilityIO(name="palette", type="list[dict]"), CapabilityIO(name="dominant", type="str")],
    latency=LatencyClass.LOW, offline_support=True, cacheable=True, deterministic=True,
    category="vision", tags=["color", "palette"],
)

scene_detect_decl = CapabilityDeclaration(
    name="scene_detect",
    description="Detect scene changes in a video",
    inputs=[CapabilityIO(name="video_path", type="string"),
            CapabilityIO(name="threshold", type="float", required=False, default=0.3)],
    outputs=[CapabilityIO(name="scenes", type="list[dict]"), CapabilityIO(name="scene_count", type="integer")],
    latency=LatencyClass.HIGH, offline_support=True, cacheable=False,
    category="vision", tags=["video", "scene", "detection"],
)

frame_extract_decl = CapabilityDeclaration(
    name="frame_extract",
    description="Extract frames from video at specified intervals",
    inputs=[CapabilityIO(name="video_path", type="string"),
            CapabilityIO(name="interval_seconds", type="float", required=False, default=1.0)],
    outputs=[CapabilityIO(name="frames", type="list[str]"), CapabilityIO(name="count", type="integer")],
    latency=LatencyClass.HIGH, offline_support=True, cacheable=False,
    category="vision", tags=["video", "frames", "extraction"],
)

track_objects_decl = CapabilityDeclaration(
    name="track_objects",
    description="Track objects across video frames",
    inputs=[CapabilityIO(name="video_path", type="string"),
            CapabilityIO(name="initial_bbox", type="list[float]", required=False)],
    outputs=[CapabilityIO(name="tracks", type="list[dict]"), CapabilityIO(name="trajectory", type="list[list]")],
    latency=LatencyClass.HIGH, offline_support=True, cacheable=False,
    category="vision", tags=["tracking", "video", "objects"],
)


def register_capabilities(registry: CapabilityRegistry) -> None:
    for decl in [
        image_analyze_decl, process_image_decl, ocr_image_decl,
        clip_analyze_decl, segment_image_decl, detect_objects_decl,
        image_similarity_decl, color_analysis_decl,
        scene_detect_decl, frame_extract_decl, track_objects_decl,
    ]:
        registry.register(decl)
