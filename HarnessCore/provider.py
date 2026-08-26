"""Day 1 -- HarnessCore.provider: the thinnest possible bridge to Gemini 3.

Teaches: talking to a tool-calling LLM over raw HTTP with nothing but the
standard library, and the neutral message format -- {"role", "text",
"tool_calls"} -- that keeps the rest of the harness provider-agnostic.

Design rules this file embodies:
  - No third-party HTTP client: urllib only, zero install-time dependencies.
  - The provider owns all wire-format translation; nothing upstream should
    need to know this is Gemini and not some other model.
  - Transient failures (rate limits, 5xx, network blips) retry with
    exponential backoff; everything else fails loudly and immediately.
"""

import json
import os
import time
import urllib.error
import urllib.request

API_ROOT = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_MODEL = "gemini-3.1-pro-preview"

_ENV_DIR = r"C:\Users\ashak\OneDrive\Desktop\claude\Harness"


def api_key():
    """Return OPEN_API_KEY from the environment, falling back to the repo's .env file."""
    value = os.environ.get("OPEN_API_KEY")
    env_file = os.path.join(_ENV_DIR, ".env")
    if not value and os.path.isfile(env_file):
        with open(env_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("OPEN_API_KEY="):
                    value = line.split("=", 1)[1].strip()
                    break
    if not value:
        raise RuntimeError(f"OPEN_API_KEY is not set. Add it to {env_file} or the environment.")
    return value


def complete(model, system, messages, tools=None):
    """Run one turn against Gemini; return {"text", "tool_calls", "usage"}.

    messages is the neutral format: {"role": "user"/"assistant"/"tool", ...}.
    tools, if given, is a list of {"schema": <functionDeclaration dict>}.
    """
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": _to_wire(messages),
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 65536},
    }
    if tools:
        body["tools"] = [{"functionDeclarations": [t["schema"] for t in tools]}]

    url = f"{API_ROOT}/{model}:generateContent?key={api_key()}"
    data = _post(url, body)

    parts = data["candidates"][0]["content"].get("parts", [])
    text = "".join(p["text"] for p in parts if "text" in p and not p.get("thought"))
    tool_calls = [
        {"name": p["functionCall"]["name"], "args": p["functionCall"].get("args", {}),
         "signature": p.get("thoughtSignature")}
        for p in parts if "functionCall" in p
    ]
    usage_meta = data.get("usageMetadata", {})
    usage = {"input": usage_meta.get("promptTokenCount", 0),
              "output": usage_meta.get("candidatesTokenCount", 0)}
    return {"text": text, "tool_calls": tool_calls, "usage": usage}


def _to_wire(messages):
    """Translate the neutral message format into Gemini's `contents` list."""
    contents = []
    for m in messages:
        if m["role"] == "user":
            contents.append({"role": "user", "parts": [{"text": m["text"]}]})
        elif m["role"] == "assistant":
            parts = [{"text": m["text"]}] if m["text"] else []
            for call in m["tool_calls"]:
                # Gemini 3 requires the thought signature to be echoed back
                # verbatim on the functionCall part it was issued with, or
                # the model loses its chain of thought on the next turn.
                parts.append({"functionCall": {"name": call["name"], "args": call["args"]},
                               "thoughtSignature": call["signature"]})
            contents.append({"role": "model", "parts": parts})
        else:  # tool
            response = {"name": m["name"], "response": {"result": m["text"]}}
            contents.append({"role": "user", "parts": [{"functionResponse": response}]})
    return contents


def _post(url, body, retries=5):
    """POST JSON via urllib, retrying transient failures with backoff."""
    data = json.dumps(body).encode("utf-8")
    last_error = None
    headers = {"Content-Type": "application/json"}
    for attempt in range(retries):
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503):
                last_error = e
                time.sleep(2**attempt * 2)
                continue
            error_body = e.read().decode("utf-8", "replace")[:400]
            raise RuntimeError(f"Gemini API error {e.code}: {error_body}")
        except (urllib.error.URLError, TimeoutError) as e:
            last_error = e
            time.sleep(2**attempt * 2)
            continue
    raise RuntimeError(f"Gemini API request failed after {retries} attempts: {last_error}")
