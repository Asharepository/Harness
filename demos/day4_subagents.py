"""Day 4 demo: a parent delegates to two sub-agents, then verifies for itself.

Run: python demos/day4_subagents.py

Checks that the parent (not a child) runs the tests, and that exactly one
session file exists afterwards -- children are ephemeral and write no log.
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from HarnessCore import Harness
from HarnessCore.session import SESSION_DIR

PYTHON = "python" if sys.platform == "win32" else "python3"
TASK = (
    "Use spawn_agent twice: delegate writing utils.py with a slugify(text) function to one "
    "child, and test_utils.py with five asserts to another; then run python3 test_utils.py "
    "yourself and report"
)


def show(kind, payload):
    """Print the parent's loop events (children run silently)."""
    if kind == "assistant":
        print(f"  assistant: {payload['text'] or [c['name'] for c in payload['tool_calls']]}")
    elif kind == "tool_end":
        print(f"  tool result [{payload['name']}]: {payload['text'][:140]!r}")


def main():
    workdir = Path(tempfile.mkdtemp(prefix="harness_sub_"))
    print(f"directory: {workdir}\nuser: {TASK}")
    harness = Harness(workdir, on_event=show, system_extra=f"On this machine, Python runs as `{PYTHON}`.")
    print(f"final: {harness.run(TASK)}\n")
    parent_calls = [(c["name"], str(c["args"])[:60]) for m in harness.messages
                    for c in m.get("tool_calls", [])]
    print(f"parent tool calls: {parent_calls}")
    print(f"session files: {sorted(p.name for p in (workdir / SESSION_DIR).glob('*.jsonl'))}")
    print(f"files: {sorted(p.name for p in workdir.iterdir() if p.is_file())}")


if __name__ == "__main__":
    main()
