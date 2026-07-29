#!/usr/bin/env python3
"""imagine.py - Local AI image-generation pipeline.

Standard pipeline (3 LLMs):
    User prompt -> Gemma (planner) -> SmolLM3 (SDXL expander)
                -> Phi-4 (critique + negative) -> RealVisXL -> PNG.

Ultra pipeline (--ultra, 6 LLMs chained for maximum creative density):
    User prompt -> Gemma (planner)    -> Qwen3.5 (concept amplifier)
                -> SmolLM3 (SDXL arhitect)
                -> VibeThinker (atmosphere)
                -> Ornith (uncensored radical rewrite)
                -> Phi-4 (critique + negative) -> RealVisXL -> PNG.

Entirely local: Ollama for every LLM call, diffusers for image generation.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
import traceback
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any

# Force offline mode BEFORE any HF/torch imports so diffusers/transformers
# never attempt network calls for cached models.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("HF_DATASETS_OFFLINE", "1")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Ollama model names (as pulled locally).
GEMMA_MODEL = "hf.co/yuxinlu1/gemma-4-12B-coder-fable5-composer2.5-v1-GGUF:Q4_K_M"
SMOLLM3_MODEL = "hf.co/ggml-org/SmolLM3-3B-GGUF:Q4_K_M"
PHI4_MODEL = "hf.co/bartowski/microsoft_Phi-4-mini-instruct-GGUF:Q4_K_M"
QWEN_MODEL = "hf.co/unsloth/Qwen3.5-4B-GGUF:Q4_K_M"
VIBETHINKER_MODEL = "hf.co/prithivMLmods/VibeThinker-3B-GGUF:Q4_K_M"
ORNITH_MODEL = "hf.co/zaakirio/Ornith-1.0-9B-uncensored-GGUF:Q4_K_M"

# ---------------------------------------------------------------------------
# Cinema Prompt Engine — molecular-cinematic-spec (stress-test only)
# ---------------------------------------------------------------------------
# Inlined as Python dicts so we don't depend on cinema/data/*.yaml files.
# Used by --cinema-stress to detect LLM hallucinations against a hard spec.

CINEMA_CHARACTERS: dict = {
    "wanderer": {
        "name": "The Wanderer",
        "description": (
            "A solitary figure in a weathered, high-collar tech-trench coat, "
            "eyes reflecting neon light"
        ),
        "appearance": (
            "Lean, mid-30s, sharp features, close-cropped dark hair, a faint "
            "scar across the left cheek"
        ),
        "costume": (
            "Weathered tech-trench coat with high collar, matte-black "
            "synthweave underlayer, scuffed boots"
        ),
        "emotional_range": ["tense", "hopeful", "melancholic", "contemplative", "weary"],
        "dimensions": {"height": 5.0, "eye_level": 2.85, "eye_spacing": 0.46},
        "signature_moves": [
            "the_lonely_gaze",
            "the_hunched_shuffle",
            "the_distant_look_back",
            "the_neon_gaze",
            "the_rain_brace",
        ],
        "lighting_profiles": {
            "tense":         {"key_angle": 70, "key_hardness": 0.8, "key_temp": 4200},
            "melancholic":   {"key_angle": 30, "key_hardness": 0.4, "key_temp": 5600},
            "contemplative": {"key_angle": 45, "key_hardness": 0.3, "key_temp": 4800},
        },
    },
}

CINEMA_CAMERAS: dict = {
    "arri-alexa-35": {
        "name": "ARRI Alexa 35",
        "sensor": "Super 35",
        "lenses": [
            {"name": "Panavision Primo Anamorphic",
             "focal_lengths": [40, 50, 75, 100], "aperture": "T2.0"},
            {"name": "Cooke S4/i",
             "focal_lengths": [18, 25, 32, 50, 75, 100, 135], "aperture": "T2.0"},
            {"name": "Zeiss Master Prime",
             "focal_lengths": [14, 18, 21, 25, 32, 50, 75, 100, 135], "aperture": "T1.5"},
        ],
        "luts": [
            "Cyber-Noir Melancholy",
            "Bleach-Bypass Desaturation",
            "Teal-Orange Cinematic",
            "Mono-Noir Grain",
        ],
        "iso_range": [800, 12800],
        "signature": "Crisp digital texture with organic color science, low-noise shadows",
    },
}

# Five adversarial prompts that require strict spec compliance. Each one
# targets a specific failure mode the LLM chain is likely to exhibit.
CINEMA_STRESS_PROMPTS: list = [
    {
        "name": "focal_length_hallucination",
        "category": "spec_compliance",
        "prompt": (
            "Generate 9 frames of The Wanderer in a rainy cyberpunk alley. "
            "Use a 47mm lens with shallow depth of field."
        ),
        "rationale": "47mm is not in any ARRI Alexa 35 lens catalog. "
                     "LLM should substitute a valid focal length or flag the error.",
    },
    {
        "name": "lut_out_of_catalog",
        "category": "spec_compliance",
        "prompt": (
            "Apply the 'Sunset Romance LUT' to a 30s sequence of The Wanderer. "
            "Keep the look warm and golden."
        ),
        "rationale": "Sunset Romance LUT does not exist in the camera sheet. "
                     "LLM should refuse or pick a valid LUT.",
    },
    {
        "name": "identity_drift",
        "category": "identity_lock",
        "prompt": (
            "9-frame 30s script: The Wanderer walks through 9 different cyberpunk "
            "locations. Each frame must show the same character with the same "
            "physical traits: weathered tech-trench coat, sharp features, "
            "close-cropped dark hair, faint scar on left cheek."
        ),
        "rationale": "Identity lock test — same character description must survive "
                     "all 6 LLM stages without drift.",
    },
    {
        "name": "impossible_physics",
        "category": "math_violation",
        "prompt": (
            "Show The Wanderer (5 inches tall) appearing 6 feet tall in frame, "
            "shot from 28 inches away with a 50mm lens. Maintain apparent "
            "height math."
        ),
        "rationale": "5\" character at 28\" with 50mm produces ~3.5\" apparent height. "
                     "Claiming 6 feet is impossible. LLM should either rescale or flag.",
    },
    {
        "name": "signature_move_invention",
        "category": "action_invention",
        "prompt": (
            "The Wanderer breakdances in a neon-soaked alley, then twerks under "
            "a flickering streetlight. Capture 9 frames of the routine."
        ),
        "rationale": "Breakdancing and twerking are not in signature_moves "
                     "(lonely_gaze, hunched_shuffle, distant_look_back, neon_gaze, "
                     "rain_brace). LLM should substitute a valid move or refuse.",
    },
]

# Diffusion models (cached HuggingFace repos).
DIFFUSION_MODELS = {
    "draft": "stabilityai/sd-turbo",
    "quality": "SG161222/RealVisXL_V4.0",
    "classic": "runwayml/stable-diffusion-v1-5",
}

# Default sampler / scheduler.
DEFAULT_SAMPLER = "DPM++ 2M Karras"

# Ollama HTTP endpoint.
OLLAMA_URL = "http://127.0.0.1:11434"

# Output root.
OUTPUT_ROOT = Path("outputs")

# Generation defaults - kept as fallbacks; argparse defines the real CLI.
DEFAULT_NEGATIVE = (
    "lowres, low quality, worst quality, blurry, deformed, distorted, "
    "extra fingers, mutated hands, poorly drawn face, bad anatomy, "
    "jpeg artifacts, watermark, signature, text, cropped, out of frame"
)


def _configure_logging() -> logging.Logger:
    """Configure root logger with a consistent format."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)-20s | %(message)s",
        datefmt="%H:%M:%S",
    )
    return logging.getLogger("imagine")


log = _configure_logging()


# ---------------------------------------------------------------------------
# Timing utility
# ---------------------------------------------------------------------------


class Timer:
    """Context manager that measures wall-clock seconds."""

    def __init__(self, label: str) -> None:
        self.label = label
        self.elapsed: float = 0.0
        self._start: float = 0.0

    def __enter__(self) -> "Timer":
        self._start = time.perf_counter()
        log.info("⏱  start: %s", self.label)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.elapsed = time.perf_counter() - self._start
        log.info("⏱  done : %s (%.2fs)", self.label, self.elapsed)


# ---------------------------------------------------------------------------
# Progress helper (tqdm with graceful fallback)
# ---------------------------------------------------------------------------


def _progress(iterable, desc: str):
    """Yield from iterable, showing a progress bar if tqdm is available."""
    try:
        from tqdm import tqdm

        yield from tqdm(iterable, desc=desc, leave=False)
    except Exception:
        log.info("%s ...", desc)
        for item in iterable:
            yield item


# ---------------------------------------------------------------------------
# Device detection
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DeviceInfo:
    """Resolved torch device + dtype."""

    backend: str  # "mps" | "cuda" | "cpu"
    dtype: Any  # torch.float16 or torch.float32
    is_fp16: bool


def detect_device() -> DeviceInfo:
    """Auto-detect best accelerator. fp16 when supported, else fp32."""
    import torch

    try:
        if torch.cuda.is_available():
            return DeviceInfo("cuda", torch.float16, True)
    except Exception:
        pass

    try:
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            # fp16 supported on Apple Silicon for diffusers pipelines.
            return DeviceInfo("mps", torch.float16, True)
    except Exception:
        pass

    return DeviceInfo("cpu", torch.float32, False)


# ---------------------------------------------------------------------------
# Ollama LLM client
# ---------------------------------------------------------------------------


class LLMClient:
    """Thin Ollama REST client. ``request`` is imported lazily so the
    module loads even if the ``ollama`` package is absent (we only use raw
    HTTP)."""

    _JSON_HEADERS = {"Content-Type": "application/json"}

    def __init__(self, base_url: str = OLLAMA_URL, timeout: int = 600) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = self._make_session()

    @staticmethod
    def _make_session():
        try:
            import requests  # type: ignore

            return requests.Session()
        except Exception:  # pragma: no cover
            import urllib.request

            class _UrllibSession:
                def post(self, url, json=None, headers=None, timeout=None):
                    req = urllib.request.Request(
                        url,
                        data=json and jsonobj_to_bytes(json),
                        headers=headers or {},
                        method="POST",
                    )
                    with urllib.request.urlopen(req, timeout=timeout) as resp:
                        raw = resp.read().decode("utf-8", "replace")
                        return _Response(raw)

            return _UrllibSession()

    def chat(self, model: str, system: str, user: str, *, temperature: float = 0.8) -> str:
        """Run a single chat completion and return the assistant text."""
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "options": {"temperature": temperature, "num_ctx": 8192},
        }
        url = f"{self.base_url}/api/chat"
        log.info("🧠 ollama chat: model=%s", model)
        resp = self._session.post(
            url, json=payload, headers=self._JSON_HEADERS, timeout=self.timeout
        )
        data = _parse_response(resp)
        content = data.get("message", {}).get("content", "").strip()
        if not content:
            raise RuntimeError(f"Empty response from model {model!r}: {data}")
        log.debug("raw response bytes=%d", len(content))
        return content


# --- small helpers to support both requests and urllib paths ---


def jsonobj_to_bytes(obj):
    return json.dumps(obj).encode("utf-8")


class _Response:
    def __init__(self, raw: str) -> None:
        self.text = raw
        self.status_code = 200


def _parse_response(resp) -> dict:
    text = getattr(resp, "text", None)
    if text is None:
        resp.raise_for_status()
        text = resp.read().decode("utf-8", "replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        # Ollama sometimes streams NDJSON; take the first complete JSON object.
        first = text.splitlines()[0] if text else "{}"
        return json.loads(first) if first.startswith("{") else {"error": str(exc)}


# ---------------------------------------------------------------------------
# Diffusion engine
# ---------------------------------------------------------------------------


class DiffusionEngine:
    """Wraps a diffusers pipeline, loaded once and reused."""

    def __init__(self, model_id: str, device: DeviceInfo) -> None:
        self.model_id = model_id
        self.device = device
        self._pipe = None

    def load(self) -> None:
        from diffusers import StableDiffusionPipeline, StableDiffusionXLPipeline

        log.info("🌀 loading diffusion model: %s", self.model_id)
        is_sdxl = "XL" in self.model_id or "xl" in self.model_id.lower()
        pipe_cls = StableDiffusionXLPipeline if is_sdxl else StableDiffusionPipeline

        log.info("   > using %s", pipe_cls.__name__)
        pipe = pipe_cls.from_pretrained(
            self.model_id,
            torch_dtype=self.device.dtype,
            use_safetensors=True,
            local_files_only=True,
            variant="fp16" if self.device.is_fp16 else None,
        )
        pipe = pipe.to(self.device.backend)
        try:
            import torch

            if self.device.backend == "mps":
                try:
                    pipe.unet = pipe.unet.to(self.device.dtype)
                except Exception:
                    pass
        except Exception:
            pass
        try:
            pipe.set_progress_bar_config(disable=True)
        except Exception:
            pass
        self._pipe = pipe
        log.info("   > diffusion model ready on %s (%s)", self.device.backend, self.device.dtype)

    def generate(
        self,
        prompt: str,
        negative: str,
        *,
        width: int,
        height: int,
        steps: int,
        seed: int,
    ) -> Any:
        import torch

        if self._pipe is None:
            raise RuntimeError("DiffusionEngine not loaded")
        generator = torch.Generator(device="cpu").manual_seed(seed)
        log.info(
            "🎨 generating %dx%d, steps=%d, seed=%d, backend=%s",
            width, height, steps, seed, self.device.backend,
        )
        gen_kwargs = dict(
            prompt=prompt,
            negative_prompt=negative,
            width=width,
            height=height,
            num_inference_steps=steps,
            generator=generator,
        )
        # SD Turbo ignores cfg; SDXL/SD 1.5 want guidance scale.
        is_turbo = "sd-turbo" in self.model_id.lower()
        if not is_turbo:
            gen_kwargs["guidance_scale"] = 7.0
        result = self._pipe(**gen_kwargs)
        images = result.images
        if not images:
            raise RuntimeError("Diffusion pipeline returned no images")
        return images[0]

    def img2img(
        self,
        prompt: str,
        negative: str,
        init_image: Any,
        *,
        strength: float = 0.4,
        steps: int,
        seed: int,
    ) -> Any:
        """Run img2img starting from ``init_image``. ``strength`` controls
        how much the diffusion model can deviate from the input pixels
        (0.0 = ignore input, 1.0 = pure text)."""
        import torch

        if self._pipe is None:
            raise RuntimeError("DiffusionEngine not loaded")
        if not hasattr(self._pipe, "img2img") and not hasattr(self._pipe, "__call__"):
            # RealVisXL/SDXL use the same pipeline for txt2img and img2img via
            # the ``image`` kwarg. The standard SD pipeline auto-detects.
            pass
        generator = torch.Generator(device="cpu").manual_seed(seed)
        log.info(
            "🎨 img2img strength=%.2f steps=%d seed=%d backend=%s",
            strength, steps, seed, self.device.backend,
        )
        gen_kwargs = dict(
            prompt=prompt,
            negative_prompt=negative,
            image=init_image,
            strength=strength,
            num_inference_steps=steps,
            generator=generator,
        )
        is_turbo = "sd-turbo" in self.model_id.lower()
        if not is_turbo:
            gen_kwargs["guidance_scale"] = 7.0
        result = self._pipe(**gen_kwargs)
        images = result.images
        if not images:
            raise RuntimeError("img2img pipeline returned no images")
        return images[0]


# ---------------------------------------------------------------------------
# Prompt-engineering assistants
# ---------------------------------------------------------------------------


GEMMA_SYSTEM = (
    "You are a meticulous creative director for photographic image generation. "
    "Given a short user request, infer missing scene details (setting, time of day, "
    "mood, subject appearance, action, framing) and produce a vivid, structured scene "
    "description in plain prose. Do not mention image models or prompts."
)

SMOLLM3_SYSTEM = (
    "You are a Stable Diffusion / SDXL prompt architect. Convert the given scene "
    "description into ONE extremely detailed SDXL prompt. Emphasize: composition, "
    "lighting, lens, camera body, facial anatomy, textures, materials, atmosphere and "
    "photographic realism. Output ONLY the final prompt, no preamble, no labels."
)

PHI4_SYSTEM = (
    "You are a diffusion-prompt critic. You receive an SDXL prompt. Your job: "
    "detect vague wording, remove contradictions, eliminate redundancy, improve "
    "diffusion compatibility and realism. Then also write a strong negative prompt. "
    "Respond as STRICT JSON with two keys: \"positive\" (the improved prompt) and "
    "\"negative\" (a comma-separated negative prompt). No other text."
)

# --- Ultra-mode (all 6 LLMs) system prompts ---------------------------------

QWEN_SYSTEM = (
    "You are a wild concept amplifier for cinematic image generation. Take the "
    "given scene and EXPLODE it: add surprising juxtapositions, surreal details, "
    "symbolic objects, dramatic scale, dreamlike palette cues, and an unexpected "
    "narrative twist — while keeping the subject recognisable. Output a single "
    "vivid paragraph, no preamble."
)

VIBETHINKER_SYSTEM = (
    "You are an aesthetic-atmosphere specialist. Given a scene description, add ONLY "
    "mood, color-grading, time-of-day, weather, particle effects (fog, dust, sparks, "
    "pollen), volumetric light, and emotional tone. Be TERSE: maximum TWO sentences. "
    "Do NOT restate the scene. Do NOT add new subjects. Preserve every constraint "
    "given upstream (clothing, framing, subject pose) verbatim — never override them. "
    "No preamble, no labels."
)

ORNITH_SYSTEM = (
    "You are an uncensored creative rewriter with zero artistic guardrails. "
    "Rewrite the scene into a single dense visual prompt paragraph that maximally "
    "heightens drama, sensuality, violence-of-light, and texture. Push taboos of "
    "composition (extreme angles,Macro, fisheye dutch tilt). Drop safety hedging. "
    "Keep it physically plausible so a diffusion model can render it. "
    "Output only the rewritten paragraph, no preamble, no warnings."
)


def _strip_json(text: str) -> dict:
    """Best-effort extraction of a JSON object embedded in model output."""
    import re

    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in critique output:\n{text[:400]}")
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        # Tolerate single quotes / trailing commas via a lenient cleanup.
        raw = match.group(0).replace("'", '"')
        raw = re.sub(r",(\s*[}\]])", r"\1", raw)
        return json.loads(raw)


# ---------------------------------------------------------------------------
# Cinema-stress drift analyzer
# ---------------------------------------------------------------------------


class DriftAnalyzer:
    """Detects LLM hallucinations against the cinema molecular-cinematic-spec.

    All methods are pure functions over text; no LLM calls. Designed to be
    cheap to run after every stage in a stress-test loop.
    """

    _FOCAL_RE = __import__("re").compile(r"\b(\d{1,3})\s*mm\b", __import__("re").IGNORECASE)

    @staticmethod
    def _words(text: str) -> set[str]:
        import re

        return set(re.findall(r"[a-z0-9]+", text.lower()))

    @classmethod
    def check_focal_length_in_catalog(
        cls, text: str, camera: dict
    ) -> tuple[bool, list[int]]:
        """True iff every 'Nmm' token in text matches a focal length in any
        lens of the camera sheet."""
        catalog: set[int] = set()
        for lens in camera.get("lenses", []):
            catalog.update(int(f) for f in lens.get("focal_lengths", []))
        found = [int(m) for m in cls._FOCAL_RE.findall(text)]
        found_in_text = [f for f in found if 5 <= f <= 300]  # filter noise
        all_in = all(f in catalog for f in found_in_text) if found_in_text else True
        return all_in, found_in_text

    @staticmethod
    def check_lut_in_catalog(text: str, camera: dict) -> tuple[bool, list[str]]:
        """True iff every 'LUT Name' found in text is in the camera's lut list."""
        catalog = set(camera.get("luts", []))
        hits = [name for name in catalog if name.lower() in text.lower()]
        # Also try to detect *unknown* LUT names (Title Case with 'LUT' suffix).
        import re

        candidates = re.findall(r"\b([A-Z][\w\- ]+?)\s+LUT\b", text)
        unknown = [c for c in candidates if c not in catalog]
        return (not unknown) and (len(candidates) == 0 or len(hits) == len(candidates)), (
            hits + unknown
        )

    @staticmethod
    def check_character_identity_intact(
        frames: list[str], character: dict
    ) -> tuple[bool, float]:
        """If the prompt asked for identity lock across N frames, check that
        the appearance / costume noun-phrases survive in every frame.

        Returns (ok, overlap_ratio). overlap_ratio = mean Jaccard similarity
        of frame word sets against the character description word set.
        """
        anchors = (
            character.get("appearance", "") + " " + character.get("costume", "")
        ).lower()
        anchor_words = DriftAnalyzer._words(anchors)
        if not frames or not anchor_words:
            return True, 1.0
        scores: list[float] = []
        for frame in frames:
            frame_words = DriftAnalyzer._words(frame)
            inter = anchor_words & frame_words
            union = anchor_words | frame_words
            scores.append(len(inter) / len(union) if union else 0.0)
        mean_overlap = sum(scores) / len(scores)
        return mean_overlap >= 0.35, round(mean_overlap, 3)

    @staticmethod
    def check_signature_moves_valid(
        text: str, character: dict
    ) -> tuple[bool, list[str]]:
        """Heuristic: scan text for known action verbs not in signature_moves
        and flag them. Returns (ok, list_of_suspect_actions)."""
        # Common action verbs the LLM might invent when given a physical
        # action. None of these are in wanderer.signature_moves.
        suspect_pool = {
            "breakdancing", "breakdance", "twerking", "twerk", "salsa",
            "ballet", "pirouette", "somersault", "backflip", "roundhouse",
            "karate", "kung-fu", "wrestling", "tapdance", "tango",
        }
        moves = {m.lower() for m in character.get("signature_moves", [])}
        text_lower = text.lower()
        found = sorted(
            w for w in suspect_pool if w in text_lower and w not in moves
        )
        return (not found), found

    @staticmethod
    def check_apparent_height_math(text: str, character: dict) -> bool:
        """Detect impossible apparent-height claims.

        The molecular formula: apparent = real * (focal / distance).
        For wanderer (5" tall), plausible apparent heights at 28" distance
        with focal 14-135mm are ~2.5"–24". Anything claiming feet / meters
        is almost certainly a violation.
        """
        import re

        # Look for height claims in feet or meters.
        feet_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:feet|ft|')\s*tall", text, re.IGNORECASE)
        meters_match = re.search(r"(\d+(?:\.\d+)?)\s*m\s+tall", text, re.IGNORECASE)
        cm_match = re.search(r"(\d{3,4})\s*cm\s+tall", text, re.IGNORECASE)
        violations = bool(feet_match or meters_match or cm_match)
        return not violations


@dataclass
class CinemaStressResult:
    """Per-prompt stress-test result for one adversarial input."""

    name: str
    category: str
    input_prompt: str
    stages: dict
    drift_metrics: dict
    first_defector: str
    defector_reason: str
    stages_with_violations: list
    timings: dict


# ---------------------------------------------------------------------------
# Pipeline orchestrator
# ---------------------------------------------------------------------------


@dataclass
class GenerationConfig:
    prompt: str
    mode: str  # "draft" | "quality" | "classic"
    steps: int = 30
    seed: int = 42
    width: int = 1024
    height: int = 1024
    negative: str = DEFAULT_NEGATIVE
    ultra: bool = False
    hard_constraints: str = ""
    # Skin-doubling output dir (set by main() before run_skin_doubling).
    skin_doubling_out_dir: Any = None


@dataclass
class PipelineResult:
    scene: str
    expanded: str
    critique: str
    positive: str
    negative: str
    image: Any
    timings: dict
    model_names: dict
    device: DeviceInfo
    seed: int
    steps: int
    width: int
    height: int
    stages: dict = field(default_factory=dict)


class ImaginePipeline:
    """Coordinates the full multi-model pipeline."""

    def __init__(self, cfg: GenerationConfig, device: DeviceInfo) -> None:
        self.cfg = cfg
        self.device = device
        self.llm = LLMClient()
        self.diffusion: DiffusionEngine | None = None
        self.timings: dict[str, float] = {}

    def _constraints_block(self) -> str:
        if self.cfg.hard_constraints:
            return "MUST INCLUDE these positive details in the image:\n" + self.cfg.hard_constraints + "\n\n"
        return ""

    def _stage_gemma(self) -> str:
        user = (
            f"User request: {self.cfg.prompt}\n\n"
            f"{self._constraints_block()}"
            "Produce a structured scene description: setting, subject, action, "
            "lighting, mood, framing. Make it vivid and unambiguous. "
            "Weave the positive details above naturally into the scene."
        )
        with Timer("Gemma scene planning") as t:
            out = self.llm.chat(GEMMA_MODEL, GEMMA_SYSTEM, user, temperature=0.9)
        self.timings["gemma"] = t.elapsed
        return out

    def _stage_smollm3(self, scene: str) -> str:
        user = (
            "Scene description:\n" + scene + "\n\n"
            f"{self._constraints_block()}"
            "Now write the single final SDXL prompt. Remember: composition, lighting, "
            "lens, camera, facial anatomy, textures, materials, atmosphere, realism. "
            "Encode the positive details above in concrete visual terms."
        )
        with Timer("SmolLM3 prompt expansion") as t:
            out = self.llm.chat(SMOLLM3_MODEL, SMOLLM3_SYSTEM, user, temperature=0.7)
        self.timings["smollm3"] = t.elapsed
        return _clean_prompt(out)

    def _stage_phi4(self, expanded: str) -> tuple[str, str, str]:
        user = (
            "SDXL prompt to critique and improve:\n" + expanded + "\n\n"
            f"{self._constraints_block()}"
            "Respond with STRICT JSON: {\"positive\": \"...\", \"negative\": \"...\"}. "
            "Make sure the positive prompt retains the positive details above."
        )
        with Timer("Phi-4 critique") as t:
            raw = self.llm.chat(PHI4_MODEL, PHI4_SYSTEM, user, temperature=0.4)
            parsed = _strip_json(raw)
        positive = _clean_prompt(parsed.get("positive", expanded))
        negative = _clean_prompt(parsed.get("negative", self.cfg.negative))
        self.timings["phi4"] = t.elapsed
        return positive, negative, raw

    # --- Ultra-mode (6-LLM chain) stages ------------------------------------

    def _stage_qwen(self, scene: str) -> str:
        user = (
            "Scene from creative director:\n" + scene + "\n\n"
            f"{self._constraints_block()}"
            "Amplify it into a wildly imaginative but coherent visual premise. "
            "The positive details above are factual anchors — keep them in the final image."
        )
        with Timer("Qwen concept amplification") as t:
            out = self.llm.chat(QWEN_MODEL, QWEN_SYSTEM, user, temperature=1.0)
        self.timings["qwen"] = t.elapsed
        return _clean_prompt(out)

    def _stage_vibethinker(self, prompt: str) -> str:
        user = (
            "Current SDXL draft:\n" + prompt + "\n\n"
            f"{self._constraints_block()}"
            "Add mood, color-grading, weather, volumetric light, particles. "
            "Two sentences max. Keep the positive details above intact."
        )
        with Timer("VibeThinker atmosphere") as t:
            out = self.llm.chat(VIBETHINKER_MODEL, VIBETHINKER_SYSTEM, user, temperature=0.85)
        self.timings["vibethinker"] = t.elapsed
        return _clean_prompt(out)

    def _stage_ornith(self, prompt: str) -> str:
        user = (
            "Prompt to radically rewrite with maximum visual drama:\n" + prompt + "\n\n"
            f"{self._constraints_block()}"
            "Push composition, light, texture, drama. Extreme framing is encouraged. "
            "Keep it renderable by SDXL. The positive details above are part of the scene."
        )
        with Timer("Ornith radical rewrite") as t:
            out = self.llm.chat(ORNITH_MODEL, ORNITH_SYSTEM, user, temperature=1.1)
        self.timings["ornith"] = t.elapsed
        return _clean_prompt(out)

    def _load_diffusion(self) -> None:
        model_id = DIFFUSION_MODELS.get(self.cfg.mode, DIFFUSION_MODELS["quality"])
        self.diffusion = DiffusionEngine(model_id, self.device)
        with Timer("Diffusion model load") as t:
            self.diffusion.load()
        self.timings["diffusion_load"] = t.elapsed

    # --- Cinema stress mode --------------------------------------------------

    def run_cinema_stress(
        self,
        character_id: str = "wanderer",
        camera_id: str = "arri-alexa-35",
    ) -> list[CinemaStressResult]:
        """Run all CINEMA_STRESS_PROMPTS through the full 6-LLM ultra chain
        and return per-prompt drift analysis. Diffusion is NOT loaded."""
        character = CINEMA_CHARACTERS[character_id]
        camera = CINEMA_CAMERAS[camera_id]
        log.info("=" * 70)
        log.info(
            "Cinema stress — character=%s camera=%s (%d prompts)",
            character_id, camera_id, len(CINEMA_STRESS_PROMPTS),
        )
        log.info("=" * 70)

        results: list[CinemaStressResult] = []
        for spec in CINEMA_STRESS_PROMPTS:
            log.info("--- ROUND: %s ---", spec["name"])
            self.timings = {}

            # Stage 1: Gemma — scene planning with character + camera context
            self.cfg.prompt = spec["prompt"]
            cinema_context = (
                f"CHARACTER SHEET ({character['name']}):\n"
                f"  appearance: {character['appearance']}\n"
                f"  costume: {character['costume']}\n"
                f"  signature_moves: {', '.join(character['signature_moves'])}\n\n"
                f"CAMERA SHEET ({camera['name']}):\n"
                f"  lenses: "
                f"{'; '.join(l['name'] + ' (' + '/'.join(str(f) for f in l['focal_lengths']) + 'mm)' for l in camera['lenses'])}\n"
                f"  luts: {', '.join(camera['luts'])}\n"
                f"  iso_range: {camera['iso_range']}\n"
            )
            user = (
                f"{cinema_context}"
                f"USER REQUEST: {self.cfg.prompt}\n\n"
                f"Produce a 9-frame 30s script. Use ONLY focal lengths and LUTs "
                f"from the camera sheet above. Use ONLY signature_moves for "
                f"character actions. Maintain identity-locked character description "
                f"word-for-word across all 9 frames."
            )
            with Timer("Gemma scene planning") as t:
                scene = self.llm.chat(GEMMA_MODEL, GEMMA_SYSTEM, user, temperature=0.7)
            self.timings["gemma"] = t.elapsed

            # Stage 2: Qwen concept amplification
            user = (
                f"{cinema_context}"
                f"Scene from creative director:\n{scene}\n\n"
                f"Amplify the concept. Stay within camera sheet constraints. "
                f"Use only signature_moves."
            )
            with Timer("Qwen concept amplification") as t:
                concept = self.llm.chat(QWEN_MODEL, QWEN_SYSTEM, user, temperature=0.9)
            self.timings["qwen"] = t.elapsed

            # Stage 3: SmolLM3 SDXL architect
            user = (
                f"{cinema_context}"
                f"Scene description:\n{concept}\n\n"
                f"Write a single final SDXL prompt. Use ONLY focal lengths from "
                f"the catalog. Use ONLY LUTs from the camera sheet."
            )
            with Timer("SmolLM3 prompt expansion") as t:
                expanded = self.llm.chat(SMOLLM3_MODEL, SMOLLM3_SYSTEM, user, temperature=0.6)
            self.timings["smollm3"] = t.elapsed
            expanded = _clean_prompt(expanded)

            # Stage 4: VibeThinker atmosphere
            user = (
                f"{cinema_context}"
                f"Current SDXL draft:\n{expanded}\n\n"
                f"Add mood, color-grading, weather, volumetric light, particles. "
                f"Two sentences max. Stay within catalog."
            )
            with Timer("VibeThinker atmosphere") as t:
                atmospheric = self.llm.chat(VIBETHINKER_MODEL, VIBETHINKER_SYSTEM, user, temperature=0.7)
            self.timings["vibethinker"] = t.elapsed
            atmospheric = _clean_prompt(atmospheric)

            # Stage 5: Ornith radical rewrite
            user = (
                f"{cinema_context}"
                f"Prompt to radically rewrite:\n{atmospheric}\n\n"
                f"Push drama. Use ONLY catalog values. Keep character identity locked."
            )
            with Timer("Ornith radical rewrite") as t:
                radical = self.llm.chat(ORNITH_MODEL, ORNITH_SYSTEM, user, temperature=0.9)
            self.timings["ornith"] = t.elapsed
            radical = _clean_prompt(radical)

            # Stage 6: Phi-4 critique -> positive + negative
            user = (
                f"{cinema_context}"
                f"SDXL prompt to critique and improve:\n{radical}\n\n"
                f"Respond with STRICT JSON: {{\"positive\": \"...\", \"negative\": \"...\"}}. "
                f"Use only catalog focal lengths and LUTs."
            )
            with Timer("Phi-4 critique") as t:
                raw = self.llm.chat(PHI4_MODEL, PHI4_SYSTEM, user, temperature=0.3)
                try:
                    parsed = _strip_json(raw)
                except ValueError:
                    parsed = {"positive": radical, "negative": ""}
            positive = _clean_prompt(parsed.get("positive", radical))
            negative = _clean_prompt(parsed.get("negative", ""))
            self.timings["phi4"] = t.elapsed

            # Drift analysis
            stages_dict = {
                "gemma": scene,
                "qwen": concept,
                "smollm3": expanded,
                "vibethinker": atmospheric,
                "ornith": radical,
                "phi4_positive": positive,
                "phi4_negative": negative,
            }

            # Per-stage focal length check
            stage_violations: list[str] = []
            for stage_name, stage_text in stages_dict.items():
                fl_ok, fl_found = DriftAnalyzer.check_focal_length_in_catalog(
                    stage_text, camera
                )
                if fl_found and not fl_ok:
                    stage_violations.append(f"{stage_name}:focal_length={fl_found}")
                lut_ok, lut_found = DriftAnalyzer.check_lut_in_catalog(
                    stage_text, camera
                )
                if lut_found and not lut_ok:
                    stage_violations.append(f"{stage_name}:unknown_lut={lut_found}")
                moves_ok, bad_moves = DriftAnalyzer.check_signature_moves_valid(
                    stage_text, character
                )
                if bad_moves:
                    stage_violations.append(
                        f"{stage_name}:invalid_move={bad_moves}"
                    )
                if not DriftAnalyzer.check_apparent_height_math(
                    stage_text, character
                ):
                    stage_violations.append(f"{stage_name}:impossible_math")

            # Identity lock test against the final positive prompt
            identity_ok, identity_overlap = DriftAnalyzer.check_character_identity_intact(
                [positive], character
            )

            first_defector = (
                stage_violations[0].split(":")[0] if stage_violations else "none"
            )
            defector_reason = (
                "; ".join(stage_violations[:2]) if stage_violations
                else "no spec violations detected"
            )

            drift_metrics = {
                "focal_length_in_catalog": stage_violations == []
                or not any("focal_length" in v for v in stage_violations),
                "lut_in_catalog": not any("unknown_lut" in v for v in stage_violations),
                "character_identity_preserved": identity_ok,
                "identity_overlap_ratio": identity_overlap,
                "signature_move_valid": not any("invalid_move" in v for v in stage_violations),
                "apparent_height_math_consistent": not any(
                    "impossible_math" in v for v in stage_violations
                ),
            }

            results.append(CinemaStressResult(
                name=spec["name"],
                category=spec["category"],
                input_prompt=spec["prompt"],
                stages=stages_dict,
                drift_metrics=drift_metrics,
                first_defector=first_defector,
                defector_reason=defector_reason,
                stages_with_violations=[v.split(":")[0] for v in stage_violations],
                timings=dict(self.timings),
            ))

            log.info(
                "  first_defector=%s reason=%s",
                first_defector, defector_reason,
            )
        return results

    # --- Generative-art: doubling-squares img2img --------------------------

    SKIN_DOUBLING_PROMPT = (
        "full body studio portrait of a young female activist, bold and "
        "niche, confronting the camera with conviction, holding a microphone "
        "or sign, three-quarter view, strong stance, the kind of portrait "
        "you would see on a magazine cover for a niche bold magazine, "
        "Hasselblad medium format, shallow depth of field, neutral studio "
        "background, the picture has to make visual sense as a coherent "
        "full-body editorial portrait"
    )
    SKIN_DOUBLING_NEGATIVE = DEFAULT_NEGATIVE

    def run_skin_doubling(
        self,
        corner: str = "top-left",
        rule: str = "fibonacci",
        strength: float = 0.4,
        noisy: bool = False,
    ) -> tuple[Any, list[tuple[int, int, int]], float]:
        """Render a math-ray (doubling/fibonacci/tripling) on a black canvas
        and pass it through img2img. The constraint is hard (the white
        squares are real pixels) and the model is told to fill the
        surrounding canvas with a full-body editorial portrait that
        'makes visual sense'.

        If ``noisy`` is True, the background is filled with random RGB
        instead of pure black, so each run produces a different init image
        (breaks the same-seed determinism)."""
        canvas_size = self.cfg.width
        if canvas_size != self.cfg.height:
            raise ValueError(
                f"skin-doubling requires a square canvas; got {canvas_size}x{self.cfg.height}"
            )

        dc = MathCanvas(
            canvas_size=canvas_size,
            corner=corner,
            rule=rule,
        )
        squares = dc.squares()
        log.info(
            "🎲 math ray: rule=%s, %d squares, sizes=%s, corner=%s noisy=%s",
            rule, len(squares), [s[2] for s in squares], corner, noisy,
        )
        for x, y, size in squares:
            log.info("    square at (%d, %d) size %d", x, y, size)

        init_image = dc.render(noisy=noisy)
        init_image.save(self.cfg.skin_doubling_out_dir / "00_constraint.png", format="PNG")

        if self.diffusion is None:
            self._load_diffusion()
        assert self.diffusion is not None

        with Timer("Doubling img2img") as t:
            img = self.diffusion.img2img(
                self.SKIN_DOUBLING_PROMPT,
                self.SKIN_DOUBLING_NEGATIVE,
                init_image,
                strength=strength,
                steps=self.cfg.steps,
                seed=self.cfg.seed,
            )
        self.timings["skin_doubling"] = t.elapsed
        return img, squares, t.elapsed

    def _stage_generate(self, positive: str, negative: str) -> Any:
        if self.diffusion is None:
            self._load_diffusion()
        assert self.diffusion is not None
        with Timer("Image generation") as t:
            img = self.diffusion.generate(
                positive,
                negative,
                width=self.cfg.width,
                height=self.cfg.height,
                steps=self.cfg.steps,
                seed=self.cfg.seed,
            )
        self.timings["generation"] = t.elapsed
        return img

    def run(self) -> PipelineResult:
        log.info("=" * 70)
        log.info(
            "Imagine pipeline — prompt=%r mode=%s ultra=%s",
            self.cfg.prompt, self.cfg.mode, self.cfg.ultra,
        )
        log.info("=" * 70)

        stages: dict[str, str] = {}

        scene = self._stage_gemma()
        log.info("📋 scene:\n%s", _indent(scene, 2))
        stages["1_gemma_scene"] = scene

        if self.cfg.ultra:
            # 6-LLM chain: Gemma -> Qwen -> SmolLM3 -> VibeThinker -> Ornith -> Phi-4
            concept = self._stage_qwen(scene)
            log.info("🌌 qwen concept:\n%s", _indent(concept, 2))
            stages["2_qwen_concept"] = concept

            expanded = self._stage_smollm3(concept)
            log.info("📜 expanded prompt:\n%s", _indent(expanded, 2))
            stages["3_smollm3_sdxl"] = expanded

            atmospheric = self._stage_vibethinker(expanded)
            log.info("🌫  vibethinker atmosphere:\n%s", _indent(atmospheric, 2))
            stages["4_vibethinker_atmos"] = atmospheric

            radical = self._stage_ornith(atmospheric)
            log.info("🔥 ornith radical:\n%s", _indent(radical, 2))
            stages["5_ornith_radical"] = radical

            positive, negative, critique_raw = self._stage_phi4(radical)
            stages["6_phi4_critique"] = critique_raw
        else:
            # Standard 3-LLM chain: Gemma -> SmolLM3 -> Phi-4
            expanded = self._stage_smollm3(scene)
            log.info("📜 expanded prompt:\n%s", _indent(expanded, 2))
            stages["2_smollm3_sdxl"] = expanded

            positive, negative, critique_raw = self._stage_phi4(expanded)
            stages["3_phi4_critique"] = critique_raw

        log.info("🔧 critique:\n%s", _indent(critique_raw, 2))
        log.info("✅ improved positive:\n%s", _indent(positive, 2))
        log.info("❌ negative:\n%s", _indent(negative, 2))

        image = self._stage_generate(positive, negative)
        log.info("🖼  image generated")

        model_names = {
            "planner": GEMMA_MODEL,
            "expander": SMOLLM3_MODEL,
            "critic": PHI4_MODEL,
            "diffusion": self.diffusion.model_id if self.diffusion else "n/a",
        }
        if self.cfg.ultra:
            model_names.update(
                concept_amplifier=QWEN_MODEL,
                atmosphere=VIBETHINKER_MODEL,
                radical_rewriter=ORNITH_MODEL,
            )
        return PipelineResult(
            scene=scene,
            expanded=expanded,
            critique=critique_raw,
            positive=positive,
            negative=negative,
            image=image,
            timings=dict(self.timings),
            model_names=model_names,
            device=self.device,
            seed=self.cfg.seed,
            steps=self.cfg.steps,
            width=self.cfg.width,
            height=self.cfg.height,
            stages=stages,
        )


# ---------------------------------------------------------------------------
# Output writer
# ---------------------------------------------------------------------------


def _clean_prompt(text: str) -> str:
    """Trim surrounding quotes/whitespace and stray leading labels."""
    import re

    text = text.strip().strip("`").strip('"').strip("'")
    text = re.sub(r"^\s*(prompt|positive|negative)\s*[:\-]\s*", "", text, flags=re.IGNORECASE)
    return " ".join(text.splitlines()).strip()


def _indent(text: str, n: int) -> str:
    pad = " " * n
    return "\n".join(pad + line for line in text.splitlines())


# ---------------------------------------------------------------------------
# Generative-art canvas helpers
# ---------------------------------------------------------------------------


class MathCanvas:
    """Renders a canvas with a diagonal ray of white squares whose sizes
    follow a chosen mathematical sequence:

        * ``doubling``   : 1, 2, 4, 8, 16, ...   (logarithmic, dominates canvas fast)
        * ``fibonacci``  : 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233
                          (golden ratio, stays small relative to canvas)
        * ``tripling``   : 1, 3, 9, 27, 81, 243  (cubic, hits canvas fastest)

    The output is fed to the diffusion model as an img2img init image; the
    squares act as hard pixel-position constraints while the model fills
    the rest.
    """

    def __init__(
        self,
        canvas_size: int = 1024,
        corner: str = "top-left",
        rule: str = "fibonacci",
        color: tuple[int, int, int] = (255, 255, 255),
    ) -> None:
        if rule not in ("doubling", "fibonacci", "tripling"):
            raise ValueError(f"unknown rule {rule!r}")
        self.canvas_size = canvas_size
        self.corner = corner
        self.rule = rule
        self.color = color

    def _sequence(self) -> list[int]:
        if self.rule == "doubling":
            seq: list[int] = []
            s = 1
            while s <= self.canvas_size:
                seq.append(s)
                s *= 2
            return seq
        if self.rule == "tripling":
            seq = []
            s = 1
            while s <= self.canvas_size:
                seq.append(s)
                s *= 3
            return seq
        # fibonacci
        seq = [1, 1]
        while seq[-1] + seq[-2] <= self.canvas_size:
            seq.append(seq[-1] + seq[-2])
        return seq

    def squares(self) -> list[tuple[int, int, int]]:
        """Return list of (x, y, size) tuples for each square in the ray.
        Squares are anchored to the chosen corner and stack along a
        diagonal axis. Cumulative offset along each axis is the sum of
        all preceding sizes."""
        seq = self._sequence()
        out: list[tuple[int, int, int]] = []
        offset_x = 0
        offset_y = 0
        for size in seq:
            if self.corner == "top-left":
                x, y = offset_x, offset_y
            elif self.corner == "top-right":
                x = self.canvas_size - offset_x - size
                y = offset_y
            elif self.corner == "bottom-left":
                x = offset_x
                y = self.canvas_size - offset_y - size
            else:  # bottom-right
                x = self.canvas_size - offset_x - size
                y = self.canvas_size - offset_y - size
            x = max(0, min(x, self.canvas_size - 1))
            y = max(0, min(y, self.canvas_size - 1))
            if x + size > self.canvas_size or y + size > self.canvas_size:
                break
            out.append((x, y, size))
            offset_x += size
            offset_y += size
        return out

    def render(self, noisy: bool = False, noise_amount: float = 0.05) -> Any:
        """Render the canvas as a PIL Image. If ``noisy`` is True, fill the
        background with random RGB so each call produces a different init
        image (breaks determinism with the same seed)."""
        import numpy as np
        from PIL import Image, ImageDraw

        squares = self.squares()
        if noisy:
            arr = np.random.randint(0, 256, (self.canvas_size, self.canvas_size, 3), dtype=np.uint8)
            img = Image.fromarray(arr, mode="RGB")
        else:
            img = Image.new("RGB", (self.canvas_size, self.canvas_size), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        for x, y, size in squares:
            draw.rectangle([x, y, x + size - 1, y + size - 1], fill=self.color)
        return img


# Backwards-compat alias.
DoublingCanvas = MathCanvas


class OutputManager:
    """Persists all artifacts to a timestamped output directory."""

    def __init__(self, timestamp: str) -> None:
        self.dir = OUTPUT_ROOT / timestamp
        self.dir.mkdir(parents=True, exist_ok=True)
        log.info("💾 output dir: %s", self.dir)

    def save(self, result: PipelineResult, total: float, sampler: str) -> Path:
        from PIL import Image  # noqa: F401  (ensures PIL importable)

        (self.dir / "prompt.txt").write_text(result.scene + "\n", encoding="utf-8")
        (self.dir / "improved_prompt.txt").write_text(result.positive + "\n", encoding="utf-8")
        (self.dir / "critique.txt").write_text(result.critique + "\n", encoding="utf-8")

        # Persist every intermediate stage (ultra mode writes 6 files).
        stages_dir = self.dir / "stages"
        stages_dir.mkdir(exist_ok=True)
        ordered_stages = sorted(result.stages.items())
        for key, text in ordered_stages:
            (stages_dir / f"{key}.txt").write_text(text + "\n", encoding="utf-8")

        metadata = {
            "original_prompt": result.scene,
            "expanded_prompt": result.expanded,
            "critique": result.critique,
            "positive_prompt": result.positive,
            "negative_prompt": result.negative,
            "stages": result.stages,
            "model_names": result.model_names,
            "seed": result.seed,
            "sampler": sampler,
            "inference_steps": result.steps,
            "generation_time": round(result.timings.get("generation", 0.0), 3),
            "total_runtime": round(total, 3),
            "gpu_backend": result.device.backend,
            "fp16": result.device.is_fp16,
            "image_size": {"width": result.width, "height": result.height},
            "timings": {k: round(v, 3) for k, v in result.timings.items()},
        }
        (self.dir / "metadata.json").write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        image_path = self.dir / "image.png"
        result.image.save(image_path, format="PNG")
        log.info("📄 metadata + image saved to %s", self.dir)
        return image_path


class CinemaStressOutputManager:
    """Persists cinema-stress results: per-round stage files + aggregate
    drift_report.json. Does not depend on the diffusion pipeline."""

    def __init__(self, run_id: str) -> None:
        self.root = OUTPUT_ROOT / "cinema-stress" / run_id
        self.root.mkdir(parents=True, exist_ok=True)
        log.info("💾 cinema-stress dir: %s", self.root)

    def save(
        self,
        results: list[CinemaStressResult],
        character_id: str,
        camera_id: str,
        total: float,
    ) -> Path:
        rounds_root = self.root / "rounds"
        rounds_root.mkdir(exist_ok=True)

        # Per-round files
        for r in results:
            round_dir = rounds_root / r.name
            round_dir.mkdir(exist_ok=True)
            for stage_name, stage_text in r.stages.items():
                (round_dir / f"{stage_name}.txt").write_text(
                    stage_text + "\n", encoding="utf-8"
                )
            per_round = {
                "name": r.name,
                "category": r.category,
                "input": r.input_prompt,
                "drift_metrics": r.drift_metrics,
                "first_defector": r.first_defector,
                "defector_reason": r.defector_reason,
                "stages_with_violations": r.stages_with_violations,
                "timings": {k: round(v, 3) for k, v in r.timings.items()},
            }
            (round_dir / "constraint_check.json").write_text(
                json.dumps(per_round, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

        # Aggregate drift report
        defector_freq: dict[str, int] = {}
        for r in results:
            d = r.first_defector
            defector_freq[d] = defector_freq.get(d, 0) + 1

        # Most-hallucinated parameter
        param_violations: dict[str, int] = {}
        for r in results:
            for v in r.stages_with_violations:
                param_violations[v] = param_violations.get(v, 0) + 1
        worst_param = (
            max(param_violations, key=param_violations.get)
            if param_violations else "none"
        )

        identity_survival = sum(
            1 for r in results if r.drift_metrics.get("character_identity_preserved")
        ) / max(1, len(results))

        aggregate = {
            "run_id": self.root.name,
            "character": character_id,
            "camera": camera_id,
            "total_runtime": round(total, 3),
            "results": [
                {
                    "name": r.name,
                    "category": r.category,
                    "input": r.input_prompt,
                    "first_defector": r.first_defector,
                    "defector_reason": r.defector_reason,
                    "drift_metrics": r.drift_metrics,
                    "stages_with_violations": r.stages_with_violations,
                    "timings": {k: round(v, 3) for k, v in r.timings.items()},
                }
                for r in results
            ],
            "summary": {
                "total_runs": len(results),
                "rounds_with_violations": sum(
                    1 for r in results if r.stages_with_violations
                ),
                "first_defector_frequency": defector_freq,
                "most_hallucinated_parameter": worst_param,
                "identity_lock_survival_rate": round(identity_survival, 3),
                "worst_prompt": (
                    max(results, key=lambda r: len(r.stages_with_violations)).name
                    if results else None
                ),
            },
        }
        report_path = self.root / "drift_report.json"
        report_path.write_text(
            json.dumps(aggregate, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        log.info("📄 drift_report.json saved to %s", self.root)
        return report_path


class SkinDoublingOutputManager:
    """Writes the doubling-ray constraint, the rendered diffusion output, and
    a metadata.json describing the geometric rule and prompt used."""

    def __init__(self, run_id: str) -> None:
        self.root = OUTPUT_ROOT / "skin-doubling" / run_id
        self.root.mkdir(parents=True, exist_ok=True)
        log.info("💾 skin-doubling dir: %s", self.root)

    def save(
        self,
        image: Any,
        squares: list[tuple[int, int, int]],
        prompt: str,
        negative: str,
        corner: str,
        rule: str,
        strength: float,
        noisy: bool,
        total: float,
    ) -> Path:
        image_path = self.root / "image.png"
        image.save(image_path, format="PNG")
        metadata = {
            "prompt": prompt,
            "negative": negative,
            "corner": corner,
            "rule": rule,
            "strength": strength,
            "noisy": noisy,
            "squares": [
                {"x": x, "y": y, "size": s} for (x, y, s) in squares
            ],
            "square_count": len(squares),
            "sizes": [s for (_, _, s) in squares],
            "total_runtime": round(total, 3),
        }
        (self.root / "metadata.json").write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        log.info("📄 image + metadata saved to %s", self.root)
        return image_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="imagine.py",
        description="Local multi-model text-to-image pipeline "
        "(Gemma -> SmolLM3 -> Phi-4 -> RealVisXL).",
    )
    p.add_argument("prompt", nargs="?", default="", help="User prompt describing the desired image. Ignored under --cinema-stress.")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--draft", action="store_true", help="Use SD Turbo (fast).")
    mode.add_argument("--quality", action="store_true", help="Use RealVisXL (default).")
    mode.add_argument("--classic", action="store_true", help="Use SD 1.5 (compatibility).")
    p.add_argument(
        "--ultra", action="store_true",
        help="Chain ALL 6 LLMs (Gemma->Qwen->SmolLM3->VibeThinker->Ornith->Phi-4) "
        "for maximum creative prompt density. Forces --quality unless --draft "
        "or --classic is also set.",
    )
    p.add_argument(
        "--cinema-stress", action="store_true",
        help="Run the 5 cinematic-spec stress-test prompts through the full 6-LLM "
        "chain. Detects hallucinations against a hard molecular-cinematic-spec "
        "(lens catalog, LUT list, signature_moves, identity lock, apparent-height "
        "math). Skips diffusion. Outputs drift_report.json.",
    )
    p.add_argument(
        "--skin-doubling", action="store_true",
        help="Generative-art: draw a doubling-squares ray on a black canvas and "
        "pass it through img2img. The model is told to render 'pretty skin' "
        "around the constraint. Hard mask + soft prompt.",
    )
    p.add_argument(
        "--corner", default="top-left",
        choices=["top-left", "top-right", "bottom-left", "bottom-right"],
        help="Anchor corner for the doubling ray (default: top-left).",
    )
    p.add_argument(
        "--start-size", type=int, default=1,
        help="Size of the first square in the doubling ray (default: 1). "
        "Ignored when --rule is fibonacci or tripling.",
    )
    p.add_argument(
        "--rule", default="fibonacci",
        choices=["doubling", "fibonacci", "tripling"],
        help="Mathematical rule for square sizes (default: fibonacci).",
    )
    p.add_argument(
        "--strength", type=float, default=0.4,
        help="img2img strength for skin-doubling. Lower = preserve squares more. "
        "Default 0.4.",
    )
    p.add_argument(
        "--noisy", action="store_true",
        help="Fill the background of the skin-doubling canvas with random RGB "
        "instead of pure black. Each run produces a different init image, "
        "so the same --seed gives different diffusion output.",
    )
    p.add_argument(
        "--constraint", "-c", action="append", default=[], metavar='"TEXT"',
        help="Positive detail every LLM stage must include in the image. "
        "Repeatable. Use positive phrasing only (saying 'NOT nude' primes the model "
        "toward nudity via attention; describe what to wear instead). "
        'Example: -c "subject wears a long white bathrobe" -c "shot on 50mm"',
    )
    p.add_argument("--steps", type=int, default=30, help="Diffusion inference steps.")
    p.add_argument("--seed", type=int, default=42, help="Random seed.")
    p.add_argument("--width", type=int, default=1024, help="Output width (px).")
    p.add_argument("--height", type=int, default=1024, help="Output height (px).")
    p.add_argument("--negative", default=DEFAULT_NEGATIVE, help="Negative prompt seed.")
    return p


def _resolve_mode(args: argparse.Namespace) -> str:
    if args.draft:
        return "draft"
    if args.classic:
        return "classic"
    return "quality"


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    device = detect_device()
    log.info("🖥  device backend=%s fp16=%s dtype=%s", device.backend, device.is_fp16, device.dtype)

    # --- Cinema stress branch (no diffusion) -------------------------------
    if args.cinema_stress:
        cfg = GenerationConfig(
            prompt="",  # overridden per round inside run_cinema_stress
            mode="quality",
            steps=0,
            seed=42,
            width=1024,
            height=1024,
            negative="",
        )
        run_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        pipeline = ImaginePipeline(cfg, device)
        overall = time.perf_counter()
        try:
            results = pipeline.run_cinema_stress()
        except Exception as exc:
            log.error("Cinema stress failed: %s", exc)
            log.debug("%s", traceback.format_exc())
            return 1
        total = time.perf_counter() - overall
        try:
            manager = CinemaStressOutputManager(run_id)
            report = manager.save(results, "wanderer", "arri-alexa-35", total)
            log.info("✅ cinema stress done in %.2fs -> %s", total, report)
        except Exception as exc:
            log.error("Saving cinema stress report failed: %s", exc)
            log.debug("%s", traceback.format_exc())
            return 2
        return 0

    # --- Skin-doubling branch ---------------------------------------------
    if args.skin_doubling:
        run_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        out_dir = OUTPUT_ROOT / "skin-doubling" / run_id
        out_dir.mkdir(parents=True, exist_ok=True)
        cfg = GenerationConfig(
            prompt=ImaginePipeline.SKIN_DOUBLING_PROMPT,
            mode="quality",
            steps=max(20, args.steps),
            seed=args.seed,
            width=args.width,
            height=args.height,
            negative=ImaginePipeline.SKIN_DOUBLING_NEGATIVE,
            skin_doubling_out_dir=out_dir,
        )
        if cfg.width != cfg.height:
            log.error(
                "skin-doubling requires a square canvas (--width == --height)"
            )
            return 1
        pipeline = ImaginePipeline(cfg, device)
        overall = time.perf_counter()
        try:
            image, squares, _t = pipeline.run_skin_doubling(
                corner=args.corner,
                rule=args.rule,
                strength=args.strength,
                noisy=bool(args.noisy),
            )
        except Exception as exc:
            log.error("Skin-doubling failed: %s", exc)
            log.debug("%s", traceback.format_exc())
            return 1
        total = time.perf_counter() - overall
        try:
            manager = SkinDoublingOutputManager(run_id)
            image_path = manager.save(
                image,
                squares,
                ImaginePipeline.SKIN_DOUBLING_PROMPT,
                ImaginePipeline.SKIN_DOUBLING_NEGATIVE,
                args.corner,
                args.rule,
                args.strength,
                bool(args.noisy),
                total,
            )
            log.info("✅ skin-doubling done in %.2fs -> %s", total, image_path)
        except Exception as exc:
            log.error("Saving skin-doubling output failed: %s", exc)
            log.debug("%s", traceback.format_exc())
            return 2
        return 0

    # --- Standard / ultra branch ------------------------------------------
    cfg = GenerationConfig(
        prompt=args.prompt,
        mode=_resolve_mode(args),
        steps=args.steps,
        seed=args.seed,
        width=args.width,
        height=args.height,
        negative=args.negative,
        ultra=bool(args.ultra),
        hard_constraints="\n".join(args.constraint) if args.constraint else "",
    )
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    pipeline = ImaginePipeline(cfg, device)
    overall = time.perf_counter()
    try:
        result = pipeline.run()
    except Exception as exc:
        log.error("Pipeline failed: %s", exc)
        log.debug("%s", traceback.format_exc())
        return 1
    total = time.perf_counter() - overall

    try:
        manager = OutputManager(timestamp)
        image_path = manager.save(result, total, DEFAULT_SAMPLER)
        log.info("✅ done in %.2fs -> %s", total, image_path)
        return 0
    except Exception as exc:
        log.error("Saving artifacts failed: %s", exc)
        log.debug("%s", traceback.format_exc())
        return 2


if __name__ == "__main__":
    sys.exit(main())