#!/usr/bin/env python3
"""nano-code — minimal coding CLI for DeepSeek v4 Flash via nano-gpt.com"""
import os
import sys
import json
import httpx
from pathlib import Path

# ── Config ──────────────────────────────────────────────────────
CONFIG_DIR = Path.home() / ".nano"
CONFIG_FILE = CONFIG_DIR / "config.yaml"
API_BASE = "https://nano-gpt.com/api/v1"
MODEL = "deepseek/deepseek-v4-flash"

def load_api_key():
    # env
    key = os.environ.get("NANOGPT_API_KEY", "")
    if key:
        return key
    # yaml
    if CONFIG_FILE.exists():
        try:
            import yaml
            with open(CONFIG_FILE) as f:
                data = yaml.safe_load(f) or {}
            key = data.get("api_key", "")
            if key:
                return key
        except Exception:
            pass
    # plain text key file
    key_file = CONFIG_DIR / "key"
    if key_file.exists():
        return key_file.read_text().strip()
    print("No API key found. Set NANOGPT_API_KEY env var or ~/.nano/key")
    sys.exit(1)

SYSTEM_PROMPT = """You are a coding assistant powered by DeepSeek v4 Flash.
- Be concise, precise, and helpful.
- Provide code snippets with brief explanations.
- Ask clarifying questions when needed.
- Use plain language, no fluff.
"""

# ── API call ────────────────────────────────────────────────────
async def chat(messages: list, stream: bool = True):
    key = load_api_key()
    async with httpx.AsyncClient(
        base_url=API_BASE,
        timeout=httpx.Timeout(120),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
    ) as client:
        body = {
            "model": MODEL,
            "messages": messages,
            "stream": stream,
            "temperature": 0.3,
            "max_tokens": 4096,
        }
        if stream:
            async with client.stream("POST", "/chat/completions", json=body) as resp:
                if resp.status_code != 200:
                    text = await resp.aread()
                    print(f"API error {resp.status_code}: {text.decode()}")
                    return
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                print(content, end="", flush=True)
                        except Exception:
                            pass
            print()
        else:
            resp = await client.post("/chat/completions", json=body)
            if resp.status_code != 200:
                print(f"API error {resp.status_code}: {resp.text}")
                return
            result = resp.json()
            content = result["choices"][0]["message"]["content"]
            print(content)

# ── Interactive loop ────────────────────────────────────────────
async def main():
    import asyncio
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    print("nano-code — DeepSeek v4 Flash coding assistant")
    print("Commands: /clear, /read <file>, /quit\n")
    while True:
        try:
            user = input("❯ ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break
        if not user:
            continue
        if user.lower() in ("/quit", "/q", "/exit"):
            break
        if user.lower() == "/clear":
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            print("Context cleared.\n")
            continue
        if user.startswith("/read "):
            filepath = user[6:].strip()
            try:
                content = Path(os.path.expanduser(filepath)).read_text()
                print(f"--- {filepath} ---")
                print(content[:3000])
                print("--- end ---\n")
                # Add file content to conversation as context
                messages.append({"role": "user", "content": f"File: {filepath}\n```\n{content[:3000]}\n```"})
                continue
            except FileNotFoundError:
                print(f"File not found: {filepath}\n")
                continue
            except Exception as e:
                print(f"Error reading file: {e}\n")
                continue
        messages.append({"role": "user", "content": user})
        print()
        await chat(messages)
        print()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
