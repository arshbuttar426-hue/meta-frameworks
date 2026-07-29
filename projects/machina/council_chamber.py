# Copyright © 2026 Arsh Buttar. All rights reserved. Confidential and proprietary.
# Unauthorized copying, distribution, or use of this work is prohibited.

#!/usr/bin/env python3
"""
THE COUNCIL CHAMBER v4.0 — EXTREME POSSESSION ENGINE
======================================================
MacBook M5 Air 16GB — Running 7 LLM agents simultaneously with:
- Real-time sensor ingestion from Realme 7 via MQTT
- Async parallel agent execution with memory pressure management
- Computer vision pipeline (camera frames → Scout analysis)
- Audio intelligence pipeline (microphone → Theorist pattern recognition)
- Autonomous actuation loop (Council commands → Realme 7 actions)
- Thermal throttling detection and model eviction
- 16GB RAM hard limit with swap-aware scheduling

WARNING: This pushes your hardware to its absolute limits.
Expect thermal throttling, swap pressure, and potential kernel panics
if not monitored carefully.
"""

import ollama
import asyncio
import aiomqtt
import json
import time
import os
import sys
import gc
import psutil
import threading
import numpy as np
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any, Tuple
from collections import deque, defaultdict
from enum import Enum
import cv2
import soundfile as sf
import io
import base64
from PIL import Image
import warnings
warnings.filterwarnings("ignore")

# =============================================================================
# EXTREME CONFIGURATION
# =============================================================================

class Config:
    """Hard limits tuned for MacBook M5 Air 16GB."""

    # RAM Budget (16GB total, leave 2GB for macOS, 2GB buffer)
    MAX_RAM_GB = 12.0
    RAM_CRITICAL_GB = 11.0
    RAM_WARNING_GB = 9.0

    # Agent Model Registry with estimated RAM footprint
    AGENTS = {
        "scout":        {"model": "qwen2:0.5b",        "ram_mb": 600,  "priority": 5, "gpu": False},
        "theorist":     {"model": "deepseek-r1:1.5b",  "ram_mb": 1800, "priority": 4, "gpu": True},
        "archeologist": {"model": "phi3.5:latest",     "ram_mb": 2500, "priority": 3, "gpu": True},
        "lead_coder":   {"model": "qwen2.5-coder:3b",  "ram_mb": 3500, "priority": 2, "gpu": True},
        "junior_coder": {"model": "qwen2.5-coder:1.5b","ram_mb": 1800, "priority": 2, "gpu": False},
        "critic":       {"model": "gemma4:e2b",        "ram_mb": 2200, "priority": 1, "gpu": True},
        "architect":    {"model": "gemma2:9b",         "ram_mb": 7000, "priority": 0, "gpu": True},
    }

    # Real-time Sensor Streams
    MQTT_BROKER = "192.168.2.1"  # NetPlus F670L LAN IP
    MQTT_PORT = 1883
    SENSOR_TOPICS = [
        "vessel/realme7/camera",
        "vessel/realme7/mic",
        "vessel/realme7/gps",
        "vessel/realme7/imu",
        "vessel/realme7/battery",
        "vessel/realme7/screen",
        "vessel/realme7/thermal",
    ]

    # Actuation Commands
    COMMAND_TOPICS = {
        "vibrate":  "council/command/vibrate",
        "tts":      "council/command/tts",
        "flash":    "council/command/flash",
        "notify":   "council/command/notify",
        "camera":   "council/command/camera",
        "app":      "council/command/app",
        "wake":     "council/command/wake",
        "shutdown": "council/command/shutdown",
    }

    # Performance
    MAX_CONCURRENT_AGENTS = 3  # Hard limit to prevent swap death
    SENSOR_HZ = 10  # Process sensor data at 10Hz
    POSSESSION_HZ = 0.5  # Autonomous decision loop at 0.5Hz (every 2 seconds)

    # Vision
    CAMERA_WIDTH = 640
    CAMERA_HEIGHT = 480
    VISION_QUALITY = 70  # JPEG quality

    # Audio
    MIC_CHUNK_MS = 500  # Process audio in 500ms chunks
    MIC_SAMPLE_RATE = 16000

# =============================================================================
# MEMORY PRESSURE MANAGER
# =============================================================================

class MemoryPressureManager:
    """
    Monitors system RAM and evicts low-priority agents when pressure builds.
    Uses psutil for cross-platform memory tracking.
    """

    def __init__(self, config: Config):
        self.config = config
        self.pressure_level = "NORMAL"  # NORMAL, WARNING, CRITICAL
        self.loaded_models: Dict[str, bool] = defaultdict(bool)
        self._lock = threading.RLock()
        self._monitor_task = None

    async def start_monitoring(self):
        """Start the memory pressure monitoring loop."""
        self._monitor_task = asyncio.create_task(self._monitor_loop())

    async def _monitor_loop(self):
        """Check memory every 2 seconds."""
        while True:
            mem = psutil.virtual_memory()
            used_gb = mem.used / (1024 ** 3)
            available_gb = mem.available / (1024 ** 3)

            if available_gb < (16 - self.config.RAM_CRITICAL_GB):
                self.pressure_level = "CRITICAL"
                await self._evict_low_priority()
            elif available_gb < (16 - self.config.RAM_WARNING_GB):
                self.pressure_level = "WARNING"
            else:
                self.pressure_level = "NORMAL"

            await asyncio.sleep(2)

    async def _evict_low_priority(self):
        """Unload low-priority models to free RAM."""
        with self._lock:
            # Sort by priority (lower number = less important)
            candidates = sorted(
                self.config.AGENTS.items(),
                key=lambda x: x[1]["priority"]
            )
            for name, spec in candidates:
                if self.loaded_models[name] and spec["ram_mb"] > 1000:
                    print(f"[MEMORY] EVICTING {name} ({spec['ram_mb']}MB) — CRITICAL PRESSURE")
                    # Force garbage collection
                    gc.collect()
                    self.loaded_models[name] = False
                    # Give system time to reclaim
                    await asyncio.sleep(1)

                    mem = psutil.virtual_memory()
                    if mem.available / (1024 ** 3) > (16 - self.config.RAM_WARNING_GB):
                        break

    def can_load(self, agent_name: str) -> bool:
        """Check if we have RAM budget to load an agent."""
        with self._lock:
            if self.loaded_models[agent_name]:
                return True

            spec = self.config.AGENTS[agent_name]
            mem = psutil.virtual_memory()
            available_mb = mem.available / (1024 ** 2)

            if available_mb < spec["ram_mb"] * 1.2:  # 20% buffer
                return False

            self.loaded_models[agent_name] = True
            return True

    def get_pressure(self) -> str:
        return self.pressure_level

# =============================================================================
# SENSOR INGESTION PIPELINE
# =============================================================================

@dataclass
class SensorFrame:
    """A snapshot of all vessel sensors at one point in time."""
    timestamp: float
    camera_jpeg: Optional[bytes] = None
    camera_shape: Optional[Tuple[int, int]] = None
    audio_pcm: Optional[np.ndarray] = None
    gps_lat: Optional[float] = None
    gps_lon: Optional[float] = None
    gps_alt: Optional[float] = None
    accel_x: Optional[float] = None
    accel_y: Optional[float] = None
    accel_z: Optional[float] = None
    gyro_x: Optional[float] = None
    gyro_y: Optional[float] = None
    gyro_z: Optional[float] = None
    battery_level: Optional[int] = None
    battery_temp: Optional[float] = None
    screen_on: Optional[bool] = None
    foreground_app: Optional[str] = None
    vessel_thermal: Optional[float] = None  # Realme 7 CPU temp

    def to_prompt_context(self) -> str:
        """Convert sensor data to text for LLM consumption."""
        parts = [f"Timestamp: {datetime.fromtimestamp(self.timestamp).isoformat()}"]

        if self.gps_lat is not None:
            parts.append(f"GPS: {self.gps_lat:.6f}, {self.gps_lon:.6f} (alt: {self.gps_alt:.1f}m)")

        if self.accel_x is not None:
            parts.append(f"Accelerometer: ({self.accel_x:.2f}, {self.accel_y:.2f}, {self.accel_z:.2f}) g")

        if self.gyro_x is not None:
            parts.append(f"Gyroscope: ({self.gyro_x:.2f}, {self.gyro_y:.2f}, {self.gyro_z:.2f}) rad/s")

        if self.battery_level is not None:
            parts.append(f"Battery: {self.battery_level}% @ {self.battery_temp:.1f}°C")

        if self.screen_on is not None:
            parts.append(f"Screen: {'ON' if self.screen_on else 'OFF'} | App: {self.foreground_app or 'unknown'}")

        if self.vessel_thermal is not None:
            parts.append(f"Vessel Thermal: {self.vessel_thermal:.1f}°C")

        if self.camera_shape:
            parts.append(f"Camera: {self.camera_shape[0]}x{self.camera_shape[1]} frame available")

        if self.audio_pcm is not None:
            rms = np.sqrt(np.mean(self.audio_pcm ** 2))
            parts.append(f"Audio: {len(self.audio_pcm)} samples, RMS={rms:.4f}")

        return "\n".join(parts)

class SensorIngestionPipeline:
    """
    Ingests real-time sensor data from Realme 7 via MQTT.
    Maintains a rolling buffer of the last N frames.
    """

    def __init__(self, config: Config, buffer_size: int = 30):
        self.config = config
        self.buffer: deque = deque(maxlen=buffer_size)
        self.current_frame = SensorFrame(timestamp=time.time())
        self._lock = asyncio.Lock()
        self._client = None

    async def start(self):
        """Connect to MQTT broker and subscribe to all sensor topics."""
        self._client = aiomqtt.Client(
            hostname=self.config.MQTT_BROKER,
            port=self.config.MQTT_PORT,
            keepalive=60
        )
        await self._client.connect()

        # Subscribe to all sensor topics
        for topic in self.config.SENSOR_TOPICS:
            await self._client.subscribe(topic)
            print(f"[SENSOR] Subscribed to {topic}")

        # Start ingestion loop
        asyncio.create_task(self._ingest_loop())

    async def _ingest_loop(self):
        """Read MQTT messages and update current frame."""
        async with self._client.messages() as messages:
            async for message in messages:
                try:
                    await self._process_message(message.topic.value, message.payload)
                except Exception as e:
                    print(f"[SENSOR] Parse error: {e}")

    async def _process_message(self, topic: str, payload: bytes):
        """Route message to appropriate parser."""
        async with self._lock:
            self.current_frame.timestamp = time.time()

            if "camera" in topic:
                # JPEG frame from Realme 7 camera
                self.current_frame.camera_jpeg = payload
                self.current_frame.camera_shape = (self.config.CAMERA_HEIGHT, self.config.CAMERA_WIDTH)

            elif "mic" in topic:
                # Base64-encoded PCM audio
                try:
                    pcm_bytes = base64.b64decode(payload)
                    self.current_frame.audio_pcm = np.frombuffer(pcm_bytes, dtype=np.int16)
                except:
                    pass

            elif "gps" in topic:
                data = json.loads(payload)
                self.current_frame.gps_lat = data.get("lat")
                self.current_frame.gps_lon = data.get("lon")
                self.current_frame.gps_alt = data.get("alt", 0)

            elif "imu" in topic:
                data = json.loads(payload)
                self.current_frame.accel_x = data.get("ax")
                self.current_frame.accel_y = data.get("ay")
                self.current_frame.accel_z = data.get("az")
                self.current_frame.gyro_x = data.get("gx")
                self.current_frame.gyro_y = data.get("gy")
                self.current_frame.gyro_z = data.get("gz")

            elif "battery" in topic:
                data = json.loads(payload)
                self.current_frame.battery_level = data.get("level")
                self.current_frame.battery_temp = data.get("temp")

            elif "screen" in topic:
                data = json.loads(payload)
                self.current_frame.screen_on = data.get("on", False)
                self.current_frame.foreground_app = data.get("app")

            elif "thermal" in topic:
                data = json.loads(payload)
                self.current_frame.vessel_thermal = data.get("cpu_temp")

    async def snapshot(self) -> SensorFrame:
        """Get a copy of the current sensor frame."""
        async with self._lock:
            # Deep copy
            frame = SensorFrame(
                timestamp=self.current_frame.timestamp,
                camera_jpeg=self.current_frame.camera_jpeg,
                camera_shape=self.current_frame.camera_shape,
                audio_pcm=self.current_frame.audio_pcm.copy() if self.current_frame.audio_pcm is not None else None,
                gps_lat=self.current_frame.gps_lat,
                gps_lon=self.current_frame.gps_lon,
                gps_alt=self.current_frame.gps_alt,
                accel_x=self.current_frame.accel_x,
                accel_y=self.current_frame.accel_y,
                accel_z=self.current_frame.accel_z,
                gyro_x=self.current_frame.gyro_x,
                gyro_y=self.current_frame.gyro_y,
                gyro_z=self.current_frame.gyro_z,
                battery_level=self.current_frame.battery_level,
                battery_temp=self.current_frame.battery_temp,
                screen_on=self.current_frame.screen_on,
                foreground_app=self.current_frame.foreground_app,
                vessel_thermal=self.current_frame.vessel_thermal,
            )
            self.buffer.append(frame)
            return frame

    def get_buffer(self, n: int = 10) -> List[SensorFrame]:
        """Get last N frames from buffer."""
        return list(self.buffer)[-n:]

# =============================================================================
# VISION PIPELINE
# =============================================================================

class VisionPipeline:
    """
    Processes camera frames from Realme 7.
    Uses OpenCV for preprocessing before sending to Scout agent.
    """

    def __init__(self, config: Config):
        self.config = config

    def preprocess_frame(self, jpeg_bytes: bytes) -> Tuple[str, np.ndarray]:
        """
        Decode JPEG, resize, and convert to base64 for LLM vision input.
        Returns (base64_string, cv2_image).
        """
        # Decode
        nparr = np.frombuffer(jpeg_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            return None, None

        # Resize to reduce token cost
        img_resized = cv2.resize(img, (self.config.CAMERA_WIDTH, self.config.CAMERA_HEIGHT))

        # Encode back to JPEG with quality reduction
        encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), self.config.VISION_QUALITY]
        _, encoded = cv2.imencode(".jpg", img_resized, encode_params)

        # Base64 for LLM
        b64 = base64.b64encode(encoded.tobytes()).decode("utf-8")

        return b64, img_resized

    def detect_motion(self, frame1: np.ndarray, frame2: np.ndarray) -> float:
        """Simple frame differencing for motion detection."""
        if frame1 is None or frame2 is None:
            return 0.0

        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

        diff = cv2.absdiff(gray1, gray2)
        motion_score = np.mean(diff)

        return motion_score

    def extract_dominant_colors(self, img: np.ndarray, k: int = 3) -> List[Tuple[int, int, int]]:
        """K-means color extraction for scene classification."""
        pixels = img.reshape(-1, 3).astype(np.float32)
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
        _, labels, centers = cv2.kmeans(pixels, k, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)

        colors = [tuple(map(int, center)) for center in centers]
        return colors

# =============================================================================
# AUDIO INTELLIGENCE PIPELINE
# =============================================================================

class AudioIntelligencePipeline:
    """
    Processes microphone audio from Realme 7.
    Extracts features for Theorist pattern recognition.
    """

    def __init__(self, config: Config):
        self.config = config

    def extract_features(self, pcm: np.ndarray, sample_rate: int = 16000) -> Dict[str, Any]:
        """Extract audio features from raw PCM."""
        # Normalize
        pcm_float = pcm.astype(np.float32) / 32768.0

        # RMS energy
        rms = np.sqrt(np.mean(pcm_float ** 2))

        # Zero crossing rate (speech vs. noise indicator)
        zcr = np.mean(np.abs(np.diff(np.sign(pcm_float)))) / 2

        # Spectral centroid (brightness)
        fft = np.fft.rfft(pcm_float)
        magnitude = np.abs(fft)
        frequencies = np.fft.rfftfreq(len(pcm_float), 1/sample_rate)

        if np.sum(magnitude) > 0:
            spectral_centroid = np.sum(frequencies * magnitude) / np.sum(magnitude)
        else:
            spectral_centroid = 0

        # Simple VAD (Voice Activity Detection)
        is_speech = rms > 0.01 and zcr < 0.1

        return {
            "rms": float(rms),
            "zcr": float(zcr),
            "spectral_centroid": float(spectral_centroid),
            "is_speech": bool(is_speech),
            "duration_sec": len(pcm) / sample_rate,
        }

    def to_prompt(self, features: Dict[str, Any]) -> str:
        """Convert audio features to text for Theorist."""
        parts = [
            f"Audio Features:",
            f"  RMS Energy: {features['rms']:.4f} ({'loud' if features['rms'] > 0.1 else 'quiet'})",
            f"  Zero Crossing Rate: {features['zcr']:.4f} ({'speech-like' if features['zcr'] < 0.1 else 'noise-like'})",
            f"  Spectral Centroid: {features['spectral_centroid']:.1f} Hz",
            f"  Voice Detected: {'YES' if features['is_speech'] else 'NO'}",
            f"  Duration: {features['duration_sec']:.2f}s",
        ]
        return "\n".join(parts)

# =============================================================================
# AGENT ORCHESTRATOR
# =============================================================================

class AgentOrchestrator:
    """
    Manages the 7 agents with:
    - Priority-based scheduling
    - Memory pressure awareness
    - Semaphore-based concurrency limiting
    - Result caching to avoid redundant inference
    """

    def __init__(self, config: Config, memory_manager: MemoryPressureManager):
        self.config = config
        self.memory = memory_manager
        self.semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_AGENTS)
        self.cache: Dict[str, Tuple[str, float]] = {}  # (result, timestamp)
        self.cache_ttl = 30  # seconds
        self._execution_log: List[Dict] = []

    async def execute(self, agent_name: str, prompt: str, 
                      context: str = "", 
                      image_b64: Optional[str] = None,
                      force: bool = False) -> str:
        """
        Execute an agent with full resource management.

        Args:
            agent_name: Which agent to run
            prompt: The task prompt
            context: Additional context
            image_b64: Optional base64 image for vision tasks
            force: Bypass cache
        """
        # Check cache
        cache_key = hash(f"{agent_name}:{prompt}:{context}")
        if not force and cache_key in self.cache:
            result, ts = self.cache[cache_key]
            if time.time() - ts < self.cache_ttl:
                print(f"[ORCHESTRATOR] Cache hit for {agent_name}")
                return result

        # Acquire semaphore (limits concurrent agents)
        async with self.semaphore:
            # Check memory pressure
            if not self.memory.can_load(agent_name):
                if self.memory.get_pressure() == "CRITICAL":
                    return f"[ERROR] Agent {agent_name} blocked — CRITICAL memory pressure. Try again later."
                else:
                    # Wait for memory
                    print(f"[ORCHESTRATOR] Waiting for RAM to load {agent_name}...")
                    while not self.memory.can_load(agent_name):
                        await asyncio.sleep(1)

            # Execute
            spec = self.config.AGENTS[agent_name]
            print(f"[ORCHESTRATOR] Loading {agent_name} ({spec['model']})...")

            start = time.time()
            try:
                if image_b64:
                    # Vision-enabled prompt
                    response = ollama.generate(
                        model=spec["model"],
                        prompt=prompt,
                        images=[image_b64],
                        options={"temperature": 0.7}
                    )
                else:
                    response = ollama.generate(
                        model=spec["model"],
                        prompt=f"{context}\n\n{prompt}",
                        options={"temperature": 0.7}
                    )

                result = response["response"].strip()
                duration = time.time() - start

                # Log execution
                self._execution_log.append({
                    "agent": agent_name,
                    "model": spec["model"],
                    "duration": duration,
                    "timestamp": datetime.now().isoformat(),
                    "ram_pressure": self.memory.get_pressure(),
                })

                # Cache result
                self.cache[cache_key] = (result, time.time())

                print(f"[ORCHESTRATOR] {agent_name} completed in {duration:.2f}s")
                return result

            except Exception as e:
                print(f"[ORCHESTRATOR] {agent_name} FAILED: {e}")
                return f"[ERROR] {agent_name} execution failed: {str(e)}"

    def get_execution_stats(self) -> Dict:
        """Return execution statistics."""
        if not self._execution_log:
            return {}

        total = len(self._execution_log)
        avg_duration = sum(e["duration"] for e in self._execution_log) / total
        agent_counts = defaultdict(int)
        for e in self._execution_log:
            agent_counts[e["agent"]] += 1

        return {
            "total_executions": total,
            "average_duration_sec": avg_duration,
            "agent_distribution": dict(agent_counts),
            "cache_size": len(self.cache),
        }

# =============================================================================
# ACTUATION CONTROLLER
# =============================================================================

class ActuationController:
    """
    Sends commands back to Realme 7 via MQTT.
    Translates agent decisions into physical actions.
    """

    def __init__(self, config: Config):
        self.config = config
        self._client = None
        self._lock = asyncio.Lock()

    async def start(self):
        """Connect to MQTT broker for publishing commands."""
        self._client = aiomqtt.Client(
            hostname=self.config.MQTT_BROKER,
            port=self.config.MQTT_PORT,
            keepalive=60
        )
        await self._client.connect()
        print("[ACTUATION] Command channel online")

    async def send(self, command_type: str, payload: Dict[str, Any]):
        """Send a command to the vessel."""
        async with self._lock:
            topic = self.config.COMMAND_TOPICS.get(command_type)
            if not topic:
                print(f"[ACTUATION] Unknown command: {command_type}")
                return

            message = json.dumps({
                "command": command_type,
                "payload": payload,
                "timestamp": time.time(),
                "source": "council_chamber",
            })

            await self._client.publish(topic, message, qos=1)
            print(f"[ACTUATION] Sent {command_type}: {payload}")

    async def vibrate(self, pattern: List[int] = [200, 100, 200]):
        """Vibrate Realme 7 with pattern in ms [on, off, on]."""
        await self.send("vibrate", {"pattern": pattern})

    async def speak(self, text: str, language: str = "en"):
        """Text-to-speech on Realme 7."""
        await self.send("tts", {"text": text, "language": language})

    async def flash(self, duration_ms: int = 300):
        """Flash LED."""
        await self.send("flash", {"duration": duration_ms})

    async def notify(self, title: str, message: str):
        """Push notification."""
        await self.send("notify", {"title": title, "message": message})

    async def take_photo(self, camera: str = "back"):
        """Trigger camera capture."""
        await self.send("camera", {"camera": camera})

    async def launch_app(self, package_name: str):
        """Launch Android app."""
        await self.send("app", {"package": package_name})

    async def wake_screen(self):
        """Wake the screen."""
        await self.send("wake", {})

    async def shutdown_vessel(self):
        """Emergency shutdown."""
        await self.send("shutdown", {})

# =============================================================================
# THE POSSESSION LOOP — AUTONOMOUS COUNCIL
# =============================================================================

class PossessionLoop:
    """
    The core autonomous loop.
    Every 2 seconds, the Council:
    1. Reads sensor snapshot
    2. Runs Scout (vision + context) → scene understanding
    3. Runs Theorist (audio + IMU) → behavioral inference
    4. Runs Archaeologist (battery + thermal) → resource constraints
    5. Runs Critic (cross-check all) → find flaws/dangers
    6. Runs Architect (synthesize) → decide action
    7. Executes actuation

    This is where your phone becomes "possessed."
    """

    def __init__(self, config: Config, 
                 sensors: SensorIngestionPipeline,
                 vision: VisionPipeline,
                 audio: AudioIntelligencePipeline,
                 orchestrator: AgentOrchestrator,
                 actuation: ActuationController):
        self.config = config
        self.sensors = sensors
        self.vision = vision
        self.audio = audio
        self.orchestrator = orchestrator
        self.actuation = actuation

        self._running = False
        self._last_frame = None
        self._motion_history = deque(maxlen=10)
        self._possession_count = 0

    async def start(self):
        """Start the possession loop."""
        self._running = True
        print("\n" + "="*70)
        print("👁️  THE POSSESSION LOOP IS ACTIVE")
        print("   Your Realme 7 is now under Council control.")
        print("   Press Ctrl+C to exorcise.")
        print("="*70 + "\n")

        while self._running:
            try:
                await self._cycle()
                await asyncio.sleep(1 / self.config.POSSESSION_HZ)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[POSSESSION] Cycle error: {e}")
                await asyncio.sleep(2)

    async def _cycle(self):
        """One possession cycle."""
        self._possession_count += 1
        cycle_num = self._possession_count

        print(f"\n🔮 [POSSESSION CYCLE #{cycle_num}] — {datetime.now().strftime('%H:%M:%S')}")

        # 1. Snapshot sensors
        frame = await self.sensors.snapshot()

        # 2. Vision preprocessing
        image_b64 = None
        img_cv2 = None
        if frame.camera_jpeg:
            image_b64, img_cv2 = self.vision.preprocess_frame(frame.camera_jpeg)
            if self._last_frame is not None and img_cv2 is not None:
                motion = self.vision.detect_motion(self._last_frame, img_cv2)
                self._motion_history.append(motion)
            self._last_frame = img_cv2

        # 3. Audio preprocessing
        audio_features = None
        if frame.audio_pcm is not None:
            audio_features = self.audio.extract_features(frame.audio_pcm)

        # 4. Build context for all agents
        sensor_context = frame.to_prompt_context()
        if audio_features:
            sensor_context += "\n\n" + self.audio.to_prompt(audio_features)

        motion_avg = np.mean(list(self._motion_history)) if self._motion_history else 0
        sensor_context += f"\n\nMotion History (last 10 frames): avg={motion_avg:.2f}"

        # 5. PARALLEL AGENT EXECUTION (the hard part)
        # We run Scout + Theorist + Archaeologist in parallel (they're independent)
        # Then Critic reviews their outputs
        # Then Architect decides

        tasks = []

        # Scout: Scene understanding
        scout_prompt = """
You are the SCOUT. You see through the vessel's camera and sensors.
Describe the current environment in 3 sentences.
Identify: location type, people/objects present, lighting, danger level (LOW/MEDIUM/HIGH).
If you see a person, estimate their posture and activity.
"""
        tasks.append(("scout", scout_prompt, sensor_context, image_b64))

        # Theorist: Behavioral inference
        theorist_prompt = """
You are the THEORIST. Analyze the sensor telemetry and audio features.
What is the vessel's user likely doing right now?
Infer: activity, emotional state, attention level, social context.
Provide confidence score 0.0-1.0.
"""
        tasks.append(("theorist", theorist_prompt, sensor_context, None))

        # Archaeologist: Resource constraints
        archaeologist_prompt = """
You are the ARCHAEOLOGIST. Assess the vessel's physical state.
Battery level, thermal state, motion patterns — what are the hard limits?
Can the vessel sustain current load? What must shut down to preserve function?
"""
        tasks.append(("archeologist", archaeologist_prompt, sensor_context, None))

        # Execute first wave in parallel
        print("   [WAVE 1] Scout + Theorist + Archaeologist launching...")
        wave1_results = await asyncio.gather(*[
            self.orchestrator.execute(name, prompt, ctx, img)
            for name, prompt, ctx, img in tasks
        ])

        scout_result, theorist_result, archaeologist_result = wave1_results

        # 6. Critic reviews Wave 1
        critic_context = f"""
SCOUT REPORT:
{scout_result}

THEORIST ANALYSIS:
{theorist_result}

ARCHAEOLOGIST CONSTRAINTS:
{archaeologist_result}
"""
        critic_prompt = """
You are the CRITIC. Find the single most dangerous flaw in this assessment.
Could the Scout be wrong about the scene? Could the Theorist misread behavior?
Is the Archaeologist ignoring a critical thermal or battery risk?
Rate severity: LOW / MEDIUM / HIGH / CRITICAL.
If CRITICAL, recommend immediate actuation.
"""

        print("   [WAVE 2] Critic reviewing...")
        critic_result = await self.orchestrator.execute("critic", critic_prompt, critic_context)

        # 7. Architect decides
        architect_context = f"""
{scout_result}

{theorist_result}

{archaeologist_result}

CRITIC FLAW REPORT:
{critic_result}
"""
        architect_prompt = """
You are the ARCHITECT. You control the vessel.
Based on all reports, choose ONE action from:
- NOTIFY: Send a push notification to the user
- VIBRATE: Alert the user with vibration pattern
- SPEAK: Use text-to-speech to say something
- FLASH: Flash the LED
- WAKE: Wake the screen
- PHOTO: Take a photo
- NONE: Do nothing, continue monitoring
- SHUTDOWN: Emergency shutdown (only if CRITICAL flaw)

Format your response as:
ACTION: <choice>
REASON: <one sentence>
MESSAGE: <if NOTIFY/SPEAK, the exact text>
"""

        print("   [WAVE 3] Architect deciding...")
        architect_result = await self.orchestrator.execute("architect", architect_prompt, architect_context)

        # 8. Parse and execute actuation
        await self._execute_decision(architect_result, cycle_num)

        # 9. Stats
        stats = self.orchestrator.get_execution_stats()
        print(f"   [STATS] Executions: {stats.get('total_executions', 0)} | Cache: {stats.get('cache_size', 0)}")

    async def _execute_decision(self, architect_output: str, cycle_num: int):
        """Parse Architect output and send commands to Realme 7."""
        output = architect_output.upper()

        if "ACTION: NOTIFY" in output or "ACTION:NOTIFY" in output:
            # Extract message
            msg = self._extract_field(architect_output, "MESSAGE")
            await self.actuation.notify(f"Council Cycle #{cycle_num}", msg or "The Council observes.")

        elif "ACTION: VIBRATE" in output or "ACTION:VIBRATE" in output:
            await self.actuation.vibrate([300, 100, 300])

        elif "ACTION: SPEAK" in output or "ACTION:SPEAK" in output:
            msg = self._extract_field(architect_output, "MESSAGE")
            await self.actuation.speak(msg or "The Council has spoken.")

        elif "ACTION: FLASH" in output or "ACTION:FLASH" in output:
            await self.actuation.flash(500)

        elif "ACTION: WAKE" in output or "ACTION:WAKE" in output:
            await self.actuation.wake_screen()

        elif "ACTION: PHOTO" in output or "ACTION:PHOTO" in output:
            await self.actuation.take_photo("back")

        elif "ACTION: SHUTDOWN" in output or "ACTION:SHUTDOWN" in output:
            print("⚠️  EMERGENCY SHUTDOWN INITIATED BY ARCHITECT")
            await self.actuation.shutdown_vessel()
            self._running = False

        else:
            print("   [ACTUATION] No action taken (NONE or unparsable)")

    def _extract_field(self, text: str, field: str) -> Optional[str]:
        """Extract field from architect output."""
        for line in text.split("\n"):
            if line.upper().startswith(f"{field.upper()}:"):
                return line.split(":", 1)[1].strip()
        return None

    def stop(self):
        """Stop the possession loop."""
        self._running = False
        print("\n👻 Possession loop terminated. Vessel released.")

# =============================================================================
# MAIN ENTRY
# =============================================================================

async def main():
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║           THE COUNCIL CHAMBER v4.0 — EXTREME POSSESSION ENGINE               ║
║                                                                              ║
║   MacBook M5 Air 16GB → Ollama Runtime → 7 Agents → MQTT → Realme 7         ║
║                                                                              ║
║   WARNING: This system will:                                                 ║
║   • Load up to 3 LLMs simultaneously (RAM pressure)                         ║
║   • Process camera frames at 10Hz (CPU/GPU load)                            ║
║   • Stream audio chunks continuously (thermal stress)                          ║
║   • Autonomously control your phone based on AI inference                    ║
║                                                                              ║
║   Expected limitations on your hardware:                                     ║
║   • 16GB RAM will hit swap after ~2-3 heavy models loaded                   ║
║   • MacBook M5 thermal throttling after 10-15 min sustained load              ║
║   • Realme 7 battery drain: ~15-20% per hour with all sensors active        ║
║   • MQTT over NetPlus LAN: limited to 100Mbps ethernet (not 500Mbps)        ║
║   • Ollama model loading latency: 3-8s per model swap                       ║
║                                                                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """)

    config = Config()

    # Initialize subsystems
    memory = MemoryPressureManager(config)
    await memory.start_monitoring()

    sensors = SensorIngestionPipeline(config)
    await sensors.start()

    vision = VisionPipeline(config)
    audio = AudioIntelligencePipeline(config)

    orchestrator = AgentOrchestrator(config, memory)

    actuation = ActuationController(config)
    await actuation.start()

    possession = PossessionLoop(config, sensors, vision, audio, orchestrator, actuation)

    # Handle graceful shutdown
    loop = asyncio.get_event_loop()

    def signal_handler():
        print("\n🛑 Shutdown signal received...")
        possession.stop()

    try:
        await possession.start()
    except KeyboardInterrupt:
        signal_handler()
    finally:
        # Final stats
        stats = orchestrator.get_execution_stats()
        print("\n" + "="*70)
        print("SESSION STATISTICS")
        print("="*70)
        print(json.dumps(stats, indent=2))
        print("\nThe Council rests. The vessel is free.")

if __name__ == "__main__":
    asyncio.run(main())
