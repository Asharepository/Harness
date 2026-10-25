"""Day 4 demo: kill the agent mid-task, then resume it from its session log.

Run: python demos/day4_crash.py

A worker process runs the task with a policy that stalls on its 4th tool call.
The parent waits until the log shows a tool call that was asked but not yet
answered, hard-kills the worker (Popen.kill is TerminateProcess on Windows and
SIGKILL elsewhere), then resumes in a fresh Harness over the same directory.
"""

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from HarnessCore import Harness, Policy
from HarnessCore.session import SESSION_DIR

TASK = "Create part1.txt through part5.txt one at a time, then SUMMARY.md describing each"
EXPECTED = [f"part{i}.txt" for i in range(1, 6)] + ["SUMMARY.md"]


class SlowPolicy(Policy):
    """Yolo, but stalls on the 4th call so a kill can land mid-call."""

    def __init__(self):
        super().__init__("yolo")
        self.calls = 0

    def check(self, call):
        self.calls += 1
        if self.calls == 4:
            time.sleep(60)
        return super().check(call)


def show(kind, payload):
    """Print each loop event so the transcript is visible on stdout."""
    if kind == "assistant":
        print(f"  assistant: {payload['text'] or [c['name'] + str(c['args'])[:50] for c in payload['tool_calls']]}")
    elif kind == "tool_end":
        print(f"  tool result [{payload['name']}]: {payload['text'][:90]!r}")


def log_has_orphan(workdir):
    """True once the log holds 3+ tool results and a call still awaiting its result."""
    for path in (workdir / SESSION_DIR).glob("*.jsonl"):
        msgs = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.endswith("}")]
        last = max((i for i, m in enumerate(msgs) if m["role"] == "assistant"), default=-1)
        answered = sum(m["role"] == "tool" for m in msgs[last + 1:])
        if sum(m["role"] == "tool" for m in msgs) >= 3 and last >= 0 and len(msgs[last]["tool_calls"]) > answered:
            return True
    return False


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "worker":
        Harness(sys.argv[2], policy=SlowPolicy(), on_event=show).run(TASK)
        return
    workdir = Path(tempfile.mkdtemp(prefix="harness_crash_"))
    print(f"directory: {workdir}\n--- phase 1: run, then kill ---")
    worker = subprocess.Popen([sys.executable, "-u", __file__, "worker", str(workdir)])
    deadline = time.time() + 120
    while time.time() < deadline and worker.poll() is None and not log_has_orphan(workdir):
        time.sleep(0.1)
    worker.kill()
    worker.wait()
    print(f"*** worker killed (exit code {worker.returncode}); files so far: "
          f"{sorted(p.name for p in workdir.iterdir() if p.is_file())}\n--- phase 2: resume ---")

    harness = Harness(workdir, on_event=show)
    print(f"resume() -> {harness.resume()}")
    for m in harness.messages:
        if m["role"] == "tool" and m["text"].startswith("Interrupted"):
            print(f"  interruption notice for {m['name']}: {m['text']!r}")
    print(f"final: {harness.run('continue the task')}")
    missing = [f for f in EXPECTED if not (workdir / f).is_file()]
    print(f"\nall six files exist: {not missing}  missing: {missing}")


if __name__ == "__main__":
    main()
