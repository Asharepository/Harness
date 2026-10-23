"""Day 3 -- HarnessCore.context: keeping a long run inside the token budget.

Teaches: context is a budget, not a log. When the transcript outgrows it, the
old turns collapse into one dense summary and only the recent tail stays
verbatim. The loop never knows -- compact() plugs into its before_turn socket.

Design rules this file embodies:
  - Token counting is a cheap estimate (chars / 4), never a tokenizer call.
  - The recent tail stays verbatim so the model's working state survives.
  - The tail never opens with a tool result whose call was summarized away.
"""

from HarnessCore import provider

CHARS_PER_TOKEN = 4
KEEP_RECENT = 6
_CLIP = 600
_SYSTEM = (
    "You compress agent transcripts. Preserve: the original task, every file "
    "created or edited and its purpose, key decisions, unresolved errors, and "
    "what remains to be done. Be dense and factual."
)


def estimate_tokens(messages):
    """Estimate a message list's size in tokens: total characters / 4."""
    return sum(len(str(m)) for m in messages) // CHARS_PER_TOKEN


def compact(model, messages, budget_tokens):
    """Return messages unchanged if within budget, else summarize all but the tail."""
    if estimate_tokens(messages) <= budget_tokens or len(messages) <= KEEP_RECENT + 1:
        return messages
    cut = len(messages) - KEEP_RECENT
    # A tool result whose assistant call was summarized away is invalid input
    # for the provider, so leading tool messages join the summarized part.
    while cut < len(messages) and messages[cut]["role"] == "tool":
        cut += 1
    lines = []
    for m in messages[:cut]:
        label = m["role"] + (f" {m['name']}" if m.get("name") else "")
        calls = ", ".join(c["name"] for c in m.get("tool_calls", []))
        lines.append(f"[{label}] {m['text'][:_CLIP]}" + (f" (calls: {calls})" if calls else ""))
    transcript = [{"role": "user", "text": "\n".join(lines)}]
    summary = provider.complete(model, _SYSTEM, transcript)["text"]
    head = {"role": "user", "text": f"[Conversation so far, compacted]\n{summary}"}
    return [head] + messages[cut:]
