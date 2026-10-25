"""Day 5 -- HarnessCore.cli: the front door -- headless runs and an interactive loop.

Teaches: the CLI adds no capability. It builds a Harness, hands it an event
printer and an approver, and gets out of the way; everything it shows is
something the Harness already emitted through on_event.

Design rules this file embodies:
  - Defaults follow context: a human gets "safe" (ask before changing anything);
    a script passing -p gets "yolo", because nobody is there to answer prompts.
  - Ctrl-C never costs work: every message is already in the session log.
"""

import argparse
import os
import sys

from HarnessCore.harness import Harness
from HarnessCore.security import Policy

_COLOR = sys.stdout.isatty()
if _COLOR and sys.platform == "win32":
    os.system("")  # enables ANSI escape processing in the Windows console


def _dim(text):
    return f"\033[2m{text}\033[0m" if _COLOR else text


def _call_line(call):
    """Render a tool call as one line: name(args), args clipped."""
    return f"{call['name']}({str(call['args'])[:100]})"


def print_event(kind, payload):
    """Print assistant text plainly, each call on a line, each result's first line dimmed."""
    if kind == "assistant" and payload["text"]:
        print(payload["text"])
    elif kind == "tool_start":
        print(f"-> {_call_line(payload)}")
    elif kind == "tool_end":
        lines = payload["text"].splitlines()
        print(_dim("  " + (lines[0][:120] if lines else "(empty)")))


def approve(call, reason):
    """Ask the human whether a call may run; anything but y/yes (or EOF) refuses."""
    try:
        answer = input(f"approve {_call_line(call)}? [y/N] ")
    except EOFError:
        return False
    return answer.strip().lower() in ("y", "yes")


def main(argv=None):
    """Parse arguments, build the Harness, and run headless or interactively."""
    ap = argparse.ArgumentParser(prog="HarnessCore", description="A minimal coding-agent harness.")
    ap.add_argument("-p", "--prompt", help="run this task headlessly, then exit")
    ap.add_argument("-d", "--workdir", default=".", help="directory the agent is jailed to")
    ap.add_argument("-m", "--model", help="model name (default: $HARNESS_MODEL or built-in)")
    ap.add_argument("--mode", choices=["safe", "yolo", "read-only"], help="default: safe; yolo with -p")
    ap.add_argument("--resume", action="store_true", help="continue the latest session")
    ap.add_argument("--max-turns", type=int, default=120)
    args = ap.parse_args(argv)

    mode = args.mode or ("yolo" if args.prompt else "safe")
    harness = Harness(args.workdir, model=args.model, policy=Policy(mode, approve),
                      on_event=print_event, max_turns=args.max_turns)
    if args.resume and not harness.resume():
        print("no previous session to resume; starting fresh")
    try:
        if args.prompt:
            harness.run(args.prompt)
            return 0
        print(f"Harness | model {harness.model} | mode {mode} | jail {harness.workdir}")
        return _repl(harness)
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


def _repl(harness):
    """Prompt loop: Ctrl-D exits, Ctrl-C interrupts the run in progress."""
    while True:
        try:
            line = input("> ").strip()
        except EOFError:
            print()
            return 0
        except KeyboardInterrupt:
            print()
            continue
        if not line:
            continue
        try:
            harness.run(line)
        except KeyboardInterrupt:
            print("\nInterrupted. The session log is safe; --resume continues it.")
            # An interrupt can strand a tool call without its result; reloading
            # from the log repairs that so the next prompt sends valid history.
            if harness.session_path:
                harness.resume(harness.session_path)
