"""Day 1 -- HarnessCore.provider: the thinnest possible bridge to OpenAI.

Teaches: talking to a tool-calling LLM over raw HTTP with nothing but the
standard library, and the neutral message format -- {"role", "text",
"tool_calls"} -- that keeps the rest of the harness provider-agnostic.

Design rules this file embodies:
  - No third-party HTTP client: urllib only, zero install-time dependencies.
  - The provider owns all wire-format translation; nothing upstream should
    need to know this is OpenAI and not some other model.
  - Transient failures (rate limits, 5xx, network blips) retry with
    exponential backoff; everything else fails loudly and immediately.
"""

import json
import os
import time
import urllib.error
import urllib.request

API_ROOT = "https://api.openai.com/v1/responses"
DEFAULT_MODEL = "gpt-4o"

_ENV_DIR = r"C:\Users\ashak\OneDrive\Desktop\claude\Harness"


def api_key():
    """Return OPENAI_API_KEY from the environment, falling back to the repo's .env file."""
    value = os.environ.get("OPENAI_API_KEY")
    env_file = os.path.join(_ENV_DIR, ".env")
    if not value and os.path.isfile(env_file):
        with open(env_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("OPENAI_API_KEY="):
                    value = line.split("=", 1)[1].strip()
                    break
    if not value:
        raise RuntimeError(f"OPENAI_API_KEY is not set. Add it to {env_file} or the environment.")
    return value


def complete(model, system, messages, tools=None):
    """Run one turn against OpenAI; return {"text", "tool_calls", "usage"}.

    messages is the neutral format: {"role": "user"/"assistant"/"tool", ...}.
    tools, if given, is a list of {"schema": <name/description/parameters dict>}.
    """
    body = {
        "model": model,
        "instructions": system,
        "input": _to_wire(messages),
        "temperature": 0.4,
        "max_output_tokens": 65536,
    }
    if tools:
        body["tools"] = [{"type": "function", **t["schema"]} for t in tools]

    data = _post(API_ROOT, body)

    text = "".join(part["text"] for item in data["output"] if item["type"] == "message"
                   for part in item["content"] if part["type"] == "output_text")
    tool_calls = [
        {"name": item["name"], "args": json.loads(item["arguments"]), "signature": item["call_id"]}
        for item in data["output"] if item["type"] == "function_call"
    ]
    usage_raw = data.get("usage", {})
    usage = {"input": usage_raw.get("input_tokens", 0), "output": usage_raw.get("output_tokens", 0)}
    return {"text": text, "tool_calls": tool_calls, "usage": usage}


def _to_wire(messages):
    """Translate the neutral message format into the Responses API `input` list."""
    items = []
    for m in messages:
        if m["role"] == "user":
            items.append({"role": "user", "content": m["text"]})
        elif m["role"] == "assistant":
            if m["text"]:
                items.append({"role": "assistant", "content": m["text"]})
            for call in m["tool_calls"]:
                items.append({"type": "function_call", "call_id": call["signature"],
                               "name": call["name"], "arguments": json.dumps(call["args"])})
        else:  # tool
            # The Responses API matches a result back to its call by call_id,
            # not by name or position -- that id has to ride along on the
            # tool message from the loop and get echoed back here verbatim.
            items.append({"type": "function_call_output", "call_id": m["signature"], "output": m["text"]})
    return items


def _post(url, body, retries=5):
    """POST JSON via urllib, retrying transient failures with backoff."""
    data = json.dumps(body).encode("utf-8")
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key()}"}
    last_error = None
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
            raise RuntimeError(f"OpenAI API error {e.code}: {error_body}")
        except (urllib.error.URLError, TimeoutError) as e:
            last_error = e
            time.sleep(2**attempt * 2)
            continue
    raise RuntimeError(f"OpenAI API request failed after {retries} attempts: {last_error}")
