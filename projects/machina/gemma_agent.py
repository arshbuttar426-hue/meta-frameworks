#!/usr/bin/env python3
"""
Gemma 4 Agent - Local AI agent with full tool access
Model: gemma4:latest (9B params) via Ollama
"""

import json
import os
import requests
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from bs4 import BeautifulSoup
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "beautifulsoup4", "lxml"])
    from bs4 import BeautifulSoup

OLLAMA_URL = "http://127.0.0.1:11434"
MODEL = "gemma4:latest"

class GemmaAgent:
    def __init__(self, model: str = MODEL):
        self.model = model
        self.history: List[Dict] = []
    
    def chat(self, prompt: str, tools: bool = True) -> str:
        """Send prompt to Ollama and get response."""
        messages = [{"role": "system", "content": self._system_prompt()}] + self.history + [{"role": "user", "content": prompt}]
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.1, "top_k": 100, "top_p": 0.9}
        }
        
        response = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=120)
        response.raise_for_status()
        result = response.json()["message"]["content"]
        
        self.history.append({"role": "user", "content": prompt})
        self.history.append({"role": "assistant", "content": result})
        return result
    
    def _system_prompt(self) -> str:
        return """You are a local AI agent with full system access. You can:
- Read/write files anywhere on the filesystem
- Execute shell commands
- Scrape web content
- Use any Python library

Available tools (call via JSON in your response):
- {"tool": "read", "path": "/absolute/path"}
- {"tool": "write", "path": "/absolute/path", "content": "..."}
- {"tool": "bash", "command": "ls -la"}
- {"tool": "scrape", "url": "https://example.com"}
- {"tool": "list", "path": "/absolute/path"}

When you need to use a tool, output ONLY the JSON tool call. I will execute it and return the result."""
    
    def execute_tool(self, tool_call: Dict) -> Any:
        """Execute a tool call and return result."""
        tool = tool_call.get("tool")
        
        if tool == "read":
            path = tool_call["path"]
            with open(path, "r") as f:
                return f.read()
        
        elif tool == "write":
            path = tool_call["path"]
            content = tool_call["content"]
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as f:
                f.write(content)
            return f"Written {len(content)} bytes to {path}"
        
        elif tool == "bash":
            cmd = tool_call["command"]
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
            return {"stdout": result.stdout, "stderr": result.stderr, "code": result.returncode}
        
        elif tool == "scrape":
            url = tool_call["url"]
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            return soup.get_text()[:50000]
        
        elif tool == "list":
            path = tool_call["path"]
            return [str(p) for p in Path(path).iterdir()]
        
        return f"Unknown tool: {tool}"

    def run(self, prompt: str) -> str:
        """Run agent loop with tool execution."""
        response = self.chat(prompt)
        
        while True:
            try:
                tool_call = json.loads(response.strip())
                if isinstance(tool_call, dict) and "tool" in tool_call:
                    result = self.execute_tool(tool_call)
                    response = self.chat(f"Tool result: {json.dumps(result)}")
                    continue
            except json.JSONDecodeError:
                pass
            break
        
        return response

def main():
    agent = GemmaAgent()
    
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
        print(agent.run(prompt))
    else:
        print(f"Gemma 4 Agent ready. Model: {MODEL}")
        print("Type 'exit' to quit.\n")
        while True:
            try:
                prompt = input(">>> ")
                if prompt.lower() in ("exit", "quit"):
                    break
                print(agent.run(prompt) + "\n")
            except KeyboardInterrupt:
                break

if __name__ == "__main__":
    main()