import os
import requests
import json

def call_oracle(name, lagna_lord, moon_sign, focus_area):
    api_key = os.getenv('GEMINI_API_KEY')
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.5-flash:generateContent?key={api_key}"
    
    # Weightage Matrix: Prioritizing Lagna Lord (Identity) over Moon (Mind)
    system_prompt = f"""
    You are the Headless AI Oracle. Generate a daily Stoic report for {name}.
    Planetary Context: Lagna Lord is {lagna_lord}, Moon Sign is {moon_sign}.
    Logic: Apply a 70% weightage to the Lagna Lord's energy and 30% to the Moon.
    Tone: Short, Stoic, and to the point.
    Focus: {focus_area}.
    """
    
    payload = {
        "contents": [{"parts": [{"text": system_prompt}]}]
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        return f"Error: {e}"

# Generate Reports
print(f"\n--- Oracle Report for Arsh ---")
print(call_oracle("Arsh", "Mercury", "Aries", "Career & Tech Growth"))

print(f"\n--- Oracle Report for Priya ---")
print(call_oracle("Priya", "Venus", "Taurus", "Emotional Balance"))
