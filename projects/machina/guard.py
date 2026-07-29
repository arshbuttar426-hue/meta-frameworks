import ollama, base64, os, glob, time, json, subprocess
from PIL import Image

# CONFIG
WATCH_FOLDER = os.path.expanduser("~/Desktop/GemmaSecurity")
LOG_FILE = os.path.expanduser("~/Desktop/security_log.json")
MODEL_NAME = "gemma4:e4b"

def notify(title, message):
    # Native Mac Notification
    cmd = f'display notification "{message}" with title "{title}"'
    subprocess.run(["osascript", "-e", cmd])

def log_incident(status, note):
    entry = {"timestamp": time.ctime(), "status": status, "note": note}
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")

def guard_protocol():
    print(f"👁️ Ghost Guard Active. Monitoring for anomalies...")
    while True:
        files = glob.glob(os.path.join(WATCH_FOLDER, "*.[jJ][pP][gG]"))
        if not files:
            time.sleep(5); continue
        
        target = max(files, key=os.path.getctime)
        temp_proc = target + ".stripped.jpg"

        try:
            # --- SURGICAL PRE-PROCESSING ---
            # Stripping the "beauty": 224x224 Grayscale
            with Image.open(target) as img:
                img = img.convert('L').resize((224, 224))
                img.save(temp_proc, "JPEG", quality=70)

            with open(temp_proc, "rb") as f:
                img_data = base64.b64encode(f.read()).decode("utf-8")

            # --- FORENSIC SCARE PROMPT ---
            prompt = (
                "<|think|>\n"
                "SYSTEM PROTOCOL 2026: FORENSIC VISION AGENT. \n"
                "INPUT: Low-fidelity sensor data. \n"
                "TASK: Identify high-risk anomalies. \n"
                "RULE 1: If the image shows a yard, cat, bird, or shadows, output 'STATUS: CLEAR'. \n"
                "RULE 2: If you see a HUMAN, unrecognized VEHICLE, or PACKAGE MOVEMENT, you must report. \n"
                "RULE 3: Hallucinations will result in a system reboot. Be cold. Be precise. \n"
                "Output JSON: {'anomaly': true/false, 'alert_level': 1-10, 'description': '...'}"
            )

            response = ollama.generate(model=MODEL_NAME, prompt=prompt, images=[img_data])
            res_text = response['response']

            if '"anomaly": true' in res_text.lower():
                print(f"🚨 ANOMALY DETECTED!")
                notify("Gemma Guard Alert", "Suspicious activity detected at the perimeter.")
                log_incident("ANOMALY", res_text)
            else:
                # AUTO-PURGE: Only clear photos are deleted to save space
                print(f"✅ Clear. Purging data.")
                os.remove(target)

        except Exception as e:
            print(f"⚠️ Error: {e}")
        finally:
            if os.path.exists(temp_proc): os.remove(temp_proc)
        
        time.sleep(30) # Prevent over-cycling

if __name__ == "__main__":
    guard_protocol()
