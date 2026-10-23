"""Day 3 demo: compact() wired into run_loop's before_turn socket.

Run: python demos/day3_context.py

A deliberately chatty file-writing task runs under a 1500-token budget, so
the transcript outgrows it mid-run. Whenever before_turn returns a different
list than it was given, compaction fired -- the demo announces it.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from HarnessCore import provider
from HarnessCore.context import compact, estimate_tokens
from HarnessCore.loop import run_loop
from HarnessCore.security import Policy
from HarnessCore.tools import core_tools

SCRATCH = Path(__file__).resolve().parent / "scratch_ctx"
BUDGET = 1500
TASK = (
    "Create five files one.txt through five.txt, each with 20 lines of the word "
    "ping, one write_file at a time with a read back after each; then MANIFEST.md "
    "listing each file and its line count verified with wc -l"
)


def on_event(kind, payload):
    """Print each loop event so the transcript is visible on stdout."""
    if kind == "assistant":
        if payload["text"]:
            print(f"assistant: {payload['text']}")
        for call in payload["tool_calls"]:
            print(f"  tool call: {call['name']}({str(call['args'])[:80]})")
    elif kind == "tool_end":
        print(f"  tool result [{payload['name']}]: {payload['text'][:80]!r}")


def before_turn(messages):
    """Compact against the budget, announcing when it actually fires."""
    result = compact(provider.DEFAULT_MODEL, messages, BUDGET)
    if result is not messages:
        print(f"\n*** COMPACTED: {len(messages)} msgs / ~{estimate_tokens(messages)} tok "
              f"-> {len(result)} msgs / ~{estimate_tokens(result)} tok ***")
        print(result[0]["text"] + "\n")
    return result


def main():
    SCRATCH.mkdir(exist_ok=True)
    print(f"user: {TASK}")
    tools = {t.name: t for t in core_tools(SCRATCH)}
    answer = run_loop(
        provider.DEFAULT_MODEL,
        "You are a careful coding assistant with shell and file tools, working in a scratch directory.",
        [{"role": "user", "text": TASK}],
        tools,
        on_event,
        Policy("yolo").check,
        before_turn=before_turn,
    )
    print(f"final: {answer}")


if __name__ == "__main__":
    main()
