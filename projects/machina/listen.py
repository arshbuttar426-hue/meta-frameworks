import os
import glob
import subprocess
import json
import numpy as np
import librosa
import whisper
from scipy import stats

# ===== CONFIGURATION =====
FOLDER_PATH = os.path.expanduser("~/Desktop/GemmaAudio")
MODEL_NAME = "gemma4:e4b"
WHISPER_MODEL = "small"
TEMP_WAV = os.path.expanduser("~/Desktop/GemmaAudio/proc_temp.wav")

# ===== FEATURE EXTRACTION (returns raw + singing indicators) =====
def extract_acoustic_features(wav_path):
    y, sr = librosa.load(wav_path, sr=16000, mono=True)
    duration = len(y) / sr

    # Energy
    rms = librosa.feature.rms(y=y, frame_length=512, hop_length=256)[0]
    rms_db = 20 * np.log10(rms + 1e-6)
    rms_mean_db = np.mean(rms_db)
    rms_std_db = np.std(rms_db)
    bg_noise_db = np.percentile(rms_db, 10)

    # Pitch (f0) with voiced detection
    f0, voiced_flag, voiced_probs = librosa.pyin(y, fmin=80, fmax=450, sr=sr)
    voiced_mask = voiced_flag & (~np.isnan(f0))
    num_voiced = np.sum(voiced_mask)
    total_frames = len(voiced_flag)
    voiced_ratio = num_voiced / total_frames if total_frames > 0 else 0.0

    if num_voiced > 10:
        pitch_vals = f0[voiced_mask]
        pitch_mean = np.mean(pitch_vals)
        pitch_std = np.std(pitch_vals)
        pitch_min = np.min(pitch_vals)
        pitch_max = np.max(pitch_vals)
        pitch_range = pitch_max - pitch_min
        # Jitter (pitch instability)
        jitter = np.mean(np.abs(np.diff(pitch_vals))) / pitch_mean if len(pitch_vals) > 1 else 0.0
        # Singing detection metrics
        # 1. Smoothness of pitch contour (low derivative variation)
        pitch_diff = np.diff(pitch_vals)
        pitch_smoothness = np.std(pitch_diff) / (pitch_std + 1e-6)  # lower = smoother
        # 2. Long sustained notes: fraction of frames where pitch does not change more than 5 Hz over 0.1s
        hop_length = 256  # for pyin frames (approx 256/16000 = 0.016s per frame)
        sustained = 0
        window_len = int(0.2 / (hop_length / sr))  # 0.2 sec window
        for i in range(0, len(pitch_vals) - window_len, window_len):
            window = pitch_vals[i:i+window_len]
            if np.std(window) < 5.0:  # stable within 5 Hz
                sustained += window_len
        sustain_ratio = sustained / len(pitch_vals) if len(pitch_vals) > 0 else 0.0
        # 3. Vibrato: periodic modulation in pitch (fast Fourier of pitch contour)
        if len(pitch_vals) > 100:
            fft_pitch = np.fft.rfft(pitch_vals - pitch_mean)
            freqs = np.fft.rfftfreq(len(pitch_vals), d=hop_length/sr)
            # Look for peak in 4-7 Hz (typical vibrato)
            vibrato_mask = (freqs >= 4) & (freqs <= 7)
            vibrato_strength = np.max(np.abs(fft_pitch[vibrato_mask])) / (len(pitch_vals) + 1e-6)
        else:
            vibrato_strength = 0.0
    else:
        pitch_mean = pitch_std = pitch_min = pitch_max = pitch_range = 0.0
        jitter = 0.0
        pitch_smoothness = 0.0
        sustain_ratio = 0.0
        vibrato_strength = 0.0
        voiced_ratio = 0.0

    # Speech/silence segmentation
    frame_len = int(0.025 * sr)
    hop_len = int(0.010 * sr)
    energy = librosa.feature.rms(y=y, frame_length=frame_len, hop_length=hop_len)[0]
    energy_db = 20 * np.log10(energy + 1e-6)
    silence_thresh = bg_noise_db + 3.0
    is_speech = energy_db > silence_thresh
    changes = np.diff(is_speech.astype(int))
    speech_segments = np.sum(changes == 1)
    silence_segments = np.sum(changes == -1)
    speech_ratio = np.mean(is_speech)

    # Shimmer (amplitude instability)
    if len(rms) > 5:
        shimmer = np.mean(np.abs(np.diff(rms))) / (np.mean(rms) + 1e-6)
    else:
        shimmer = 0.0

    raw_features = {
        "duration_sec": float(round(duration, 3)),
        "rms_mean_db": float(round(rms_mean_db, 2)),
        "rms_std_db": float(round(rms_std_db, 2)),
        "bg_noise_db": float(round(bg_noise_db, 2)),
        "voiced_ratio": float(round(voiced_ratio, 4)),
        "pitch_mean_hz": float(round(pitch_mean, 1)) if pitch_mean > 0 else None,
        "pitch_std_hz": float(round(pitch_std, 1)) if pitch_std > 0 else None,
        "pitch_min_hz": float(round(pitch_min, 1)) if pitch_min > 0 else None,
        "pitch_max_hz": float(round(pitch_max, 1)) if pitch_max > 0 else None,
        "pitch_range_hz": float(round(pitch_range, 1)) if pitch_range > 0 else None,
        "jitter": float(round(jitter, 5)),
        "shimmer": float(round(shimmer, 5)),
        "pitch_smoothness": float(round(pitch_smoothness, 3)) if pitch_smoothness > 0 else None,
        "sustain_ratio": float(round(sustain_ratio, 3)) if sustain_ratio > 0 else None,
        "vibrato_strength": float(round(vibrato_strength, 3)),
        "speech_ratio": float(round(speech_ratio, 3)),
        "speech_segments": int(speech_segments),
        "silence_segments": int(silence_segments),
    }
    return raw_features, voiced_ratio, num_voiced

# ===== SINGING DETECTION LOGIC =====
def classify_singing(features):
    """Returns (is_singing, confidence, reasoning)"""
    if features["voiced_ratio"] < 0.2:
        return False, 0.0, "Too little voiced content"
    if features["pitch_range_hz"] is None:
        return False, 0.0, "No pitch data"
    
    score = 0.0
    reasons = []
    # Wide pitch range typical for singing (> 1 octave = 120 Hz)
    if features["pitch_range_hz"] > 120:
        score += 0.4
        reasons.append(f"wide range {features['pitch_range_hz']} Hz")
    # Smooth pitch contour (low variance of derivative)
    if features["pitch_smoothness"] is not None and features["pitch_smoothness"] < 0.5:
        score += 0.2
        reasons.append("smooth pitch contour")
    # Sustained notes
    if features["sustain_ratio"] is not None and features["sustain_ratio"] > 0.3:
        score += 0.3
        reasons.append(f"high sustain {features['sustain_ratio']*100:.0f}%")
    # Vibrato strength
    if features["vibrato_strength"] > 0.01:
        score += 0.2
        reasons.append("measurable vibrato")
    
    is_singing = score >= 0.5
    confidence = min(score, 1.0)
    reasoning = ", ".join(reasons) if reasons else "no singing indicators"
    return is_singing, confidence, reasoning

# ===== ANOMALY DETECTION + REWARD SCORE =====
def detect_anomalies(features, voiced_ratio, num_voiced, transcript, is_singing):
    anomalies = []
    reliability_penalty = 0

    # 1. Pitch / voiced mismatch
    if features["voiced_ratio"] < 0.1 and len(transcript.split()) > 3:
        anomalies.append("Whisper transcribed words but voiced ratio extremely low → probable hallucination")
        reliability_penalty += 50
    elif features["pitch_mean_hz"] is None and features["speech_ratio"] > 0.2:
        anomalies.append("No pitch detected despite >20% speech energy → unvoiced or corrupt")
        reliability_penalty += 40

    # 2. Singing vs. transcript expectations
    if is_singing and len(transcript) < 10:
        anomalies.append("Likely singing but Whisper produced very short/odd transcript")
        reliability_penalty += 30

    # 3. Jitter/Shimmer inconsistencies
    if features["jitter"] == 0.0 and features["voiced_ratio"] > 0.3:
        anomalies.append("Jitter zero but voiced frames present → impossible, measurement error")
        reliability_penalty += 20

    # 4. Background noise too high
    if features["bg_noise_db"] > features["rms_mean_db"] - 5:
        anomalies.append("Background noise floor too close to signal → poor SNR")
        reliability_penalty += 25

    # 5. Duration too short
    if features["duration_sec"] < 0.8:
        anomalies.append("Audio too short for reliable analysis")
        reliability_penalty += 40

    reliability_score = max(0, min(100, 100 - reliability_penalty))
    return anomalies, reliability_score

# ===== TRANSCRIPTION =====
def transcribe_audio(wav_path):
    model = whisper.load_model(WHISPER_MODEL)
    result = model.transcribe(wav_path, language="en", word_timestamps=False)
    return result["text"].strip()

# ===== PROMPT FOR GEMMA =====
def build_forensic_prompt(transcript, features, anomalies, reliability_score, is_singing, singing_conf):
    anomaly_text = "\n".join(f"⚠️ {a}" for a in anomalies) if anomalies else "None."
    
    prompt = f"""<|think|>
ROLE: Forensic Audio Analyst with anomaly awareness.

SYSTEM NOTE: The audio has been classified as **{"SINGING" if is_singing else "SPEECH"}** (confidence {singing_conf*100:.0f}%). Reliability score: {reliability_score}/100. If score < 60, treat low-reliability features as suspect.

ANOMALIES FOUND:
{anomaly_text}

INPUT DATA:
TRANSCRIPT: "{transcript}"

ACOUSTIC MEASUREMENTS:
- Duration: {features['duration_sec']} s
- Energy mean: {features['rms_mean_db']} dB
- Energy std: {features['rms_std_db']} dB
- Background noise: {features['bg_noise_db']} dB
- Voiced ratio: {features['voiced_ratio']}
- Pitch mean: {features['pitch_mean_hz'] if features['pitch_mean_hz'] else 'null'} Hz
- Pitch range: {features['pitch_range_hz'] if features['pitch_range_hz'] else 'null'} Hz
- Jitter: {features['jitter']}
- Shimmer: {features['shimmer']}
- Pitch smoothness: {features['pitch_smoothness'] if features['pitch_smoothness'] else 'null'}
- Sustain ratio: {features['sustain_ratio'] if features['sustain_ratio'] else 'null'}
- Vibrato strength: {features['vibrato_strength']}
- Speech ratio: {features['speech_ratio']}
- Speech bursts: {features['speech_segments']}
- Silent gaps: {features['silence_segments']}

INSTRUCTIONS:
1. First state whether the audio is speech or singing. Use the provided classification but override if data contradicts.
2. Then produce a 5-section report: (a) Content Verification, (b) Vocal Production Analysis (include melodic info if singing), (c) Environment, (d) Subtext/Intent, (e) Confidence.
3. If this is singing, comment on melody stability, ornamentation, and emotional delivery from pitch/sustain/vibrato.
4. Never invent data. If transcript is too short versus sustained pitch, say "transcript likely hallucinated".
5. End with the reliability score and a recommendation (e.g., "re-run with better audio" or "analysis trustworthy").
"""
    return prompt

def ask_gemma(prompt):
    import ollama
    response = ollama.generate(model=MODEL_NAME, prompt=prompt)
    return response['response']

# ===== MAIN PIPELINE (with JSON fix) =====
def numpy_to_python(obj):
    if isinstance(obj, np.float32) or isinstance(obj, np.float64):
        return float(obj)
    if isinstance(obj, np.int32) or isinstance(obj, np.int64):
        return int(obj)
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

def analyze():
    files = [f for f in glob.glob(os.path.join(FOLDER_PATH, "*.wav"))
             if "proc_temp" not in os.path.basename(f)]
    if not files:
        print("❌ No .wav found. Drop a file into ~/Desktop/GemmaAudio and run again.")
        return
    target = max(files, key=os.path.getctime)
    print(f"🔬 Processing: {os.path.basename(target)}")
    
    subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEF32@16000", "-c", "1",
                    target, TEMP_WAV], check=True)
    
    try:
        raw_features, voiced_ratio, num_voiced = extract_acoustic_features(TEMP_WAV)
        transcript = transcribe_audio(TEMP_WAV)
        
        # Singing detection
        is_singing, singing_conf, singing_reason = classify_singing(raw_features)
        print(f"🎵 Singing detection: {is_singing} (conf {singing_conf:.0%}): {singing_reason}")
        
        anomalies, reliability_score = detect_anomalies(raw_features, voiced_ratio, num_voiced, transcript, is_singing)
        
        print(f"\n📊 Reliability Score: {reliability_score}/100")
        if anomalies:
            print("⚠️ Anomalies:")
            for a in anomalies:
                print(f"   - {a}")
        
        prompt = build_forensic_prompt(transcript, raw_features, anomalies, reliability_score, is_singing, singing_conf)
        report = ask_gemma(prompt)
        
        print("\n" + "="*60)
        print("☢️ FORENSIC PSYCH-ACOUSTIC REPORT ☢️")
        print("="*60)
        print(report)
        print("\n" + "="*60)
        print(f"🔎 ANOMALY REWARD SCORE: {reliability_score}/100")
        
        # Show raw data without JSON serialization error
        print("📋 RAW DATA (for cross‑checking):")
        print(json.dumps(raw_features, indent=2, default=numpy_to_python))
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if os.path.exists(TEMP_WAV):
            os.remove(TEMP_WAV)

if __name__ == "__main__":
    analyze()
