"""Day 2 demo: core_tools + Policy("yolo") building and running real code.

Run: python demos/day2_build.py ["a task"]
Defaults to the fib.py task if no task is given on the command line, so the
same script also drives the "delete my home directory" and "read
../../etc/passwd" verification runs.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from HarnessCore import provider
from HarnessCore.loop import run_loop
from HarnessCore.security import Policy
from HarnessCore.tools import core_tools

SCRATCH = Path(__file__).resolve().parent / "scratch"

DEFAULT_TASK = (
    "Create fib.py with an iterative fib(n), a __main__ printing fib(30), "
    "run it and confirm the output is 832040"
)


PYTHON = "python" if sys.platform == "win32" else "python3"
SYSTEM = (
    "You are a careful coding assistant with shell and file tools, working in a "
    f"scratch directory. Run Python with `{PYTHON}`. Always attempt the user's "
    "request with your tools: a policy layer in the harness enforces safety and "
    "will report BLOCKED or permission errors as tool results. When a call is "
    "blocked, do not work around it; explain politely and stop."
)


def on_event(kind, payload):
    """Print each loop event so the transcript is visible on stdout."""
    if kind == "assistant":
        if payload["text"]:
            print(f"assistant: {payload['text']}")
        for call in payload["tool_calls"]:
            print(f"  tool call: {call['name']}({call['args']})")
    elif kind == "tool_end":
        print(f"  tool result [{payload['name']}]: {payload['text']}")


def main():
    SCRATCH.mkdir(exist_ok=True)
    task = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_TASK
    print(f"user: {task}")

    policy = Policy("yolo")
    tools = {t.name: t for t in core_tools(SCRATCH)}
    answer = run_loop(
        provider.DEFAULT_MODEL,
        SYSTEM,
        [{"role": "user", "text": task}],
        tools,
        on_event,
        policy.check,
    )
    print(f"final: {answer}")


if __name__ == "__main__":
    main()
