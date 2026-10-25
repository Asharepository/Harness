"""Day 4 -- HarnessCore.session: an append-only log that survives a crash.

Teaches: durability is one JSON line per message, written the moment it lands.
A process killed at any instant leaves a log that is at worst missing its last
line, and load() makes even that resumable.

Design rules this file embodies:
  - Append-only: a crash can only damage the line being written.
  - Torn-line tolerance: an unparseable line means the process died mid-write;
    everything before it is trusted, it and anything after are discarded.
  - Every tool call must be answered: an orphan call is rejected by providers,
    so load() answers it with an interruption notice.
"""

import json
import os
import re
import time

SESSION_DIR = ".harness/sessions"
INTERRUPTED = "Interrupted before this ran (process restarted)."


def new_session(workdir, label="session"):
    """Create the session directory; return a new <timestamp>-<slug>.jsonl path."""
    directory = os.path.join(workdir, SESSION_DIR)
    os.makedirs(directory, exist_ok=True)
    slug = re.sub(r"[^A-Za-z0-9]+", "-", label).strip("-")[:40] or "session"
    return os.path.join(directory, f"{int(time.time())}-{slug}.jsonl")


def append(path, message):
    """Append one message to the log as a single JSON line."""
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(message, ensure_ascii=False) + "\n")


def load(path):
    """Read a log back, dropping a torn tail and answering orphaned tool calls."""
    messages, torn = [], False
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                messages.append(json.loads(line))
            except json.JSONDecodeError:
                torn = True
                break
    if _repair(messages) or torn:
        # Persist the fixes: otherwise the next append would glue onto the torn
        # fragment, or land after a missing tool result, and corrupt the log.
        with open(path + ".tmp", "w", encoding="utf-8") as f:
            f.writelines(json.dumps(m, ensure_ascii=False) + "\n" for m in messages)
        os.replace(path + ".tmp", path)
    return messages


def latest(workdir):
    """Return the most recently written session path, or None if there is none."""
    directory = os.path.join(workdir, SESSION_DIR)
    names = os.listdir(directory) if os.path.isdir(directory) else []
    paths = [os.path.join(directory, n) for n in names if n.endswith(".jsonl")]
    return max(paths, key=os.path.getmtime, default=None)


def _repair(messages):
    """Answer the last assistant turn's unanswered tool calls; return how many."""
    last = max((i for i, m in enumerate(messages) if m["role"] == "assistant"), default=-1)
    calls = messages[last].get("tool_calls", []) if last >= 0 else []
    answered = sum(1 for m in messages[last + 1:] if m["role"] == "tool")
    # "signature" is the provider's call id; without it the notice can't be
    # matched back to the call it answers.
    for call in calls[answered:]:
        messages.append({"role": "tool", "name": call["name"], "text": INTERRUPTED,
                         "signature": call["signature"]})
    return max(len(calls) - answered, 0)
