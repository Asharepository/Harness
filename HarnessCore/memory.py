"""Day 3 -- HarnessCore.memory: the system prompt and the notes that outlive a run.

Teaches: durable memory is a markdown file the next conversation reads at
startup. Notes ride inside the system prompt, so a brand-new session over the
same directory already knows them without a single tool call.

Design rules this file embodies:
  - Memory is plain markdown in the working directory: inspectable, editable
    and versionable by the human, with no hidden store.
  - Notes are appended, never rewritten, so a crash can lose at most the
    note being written, never the ones before it.
"""

import os
import platform

MEMORY_FILE = "Harness.md"

BASE_PROMPT = """You are Harness, a small sharp coding agent working inside one directory \
with the tools provided.
- Act, don't narrate.
- Inspect before assuming.
- Prefer edit_file for small changes.
- Verify after building by running or re-reading.
- Never repeat a failing call unchanged.
- When complete, reply with a short summary and stop calling tools."""


def build_system_prompt(workdir, extra=""):
    """Assemble base prompt + environment line + project memory + extra."""
    parts = [BASE_PROMPT, f"Platform: {platform.system()}. Working directory: {os.path.realpath(workdir)}"]
    path = os.path.join(workdir, MEMORY_FILE)
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            parts.append(f"Project memory ({MEMORY_FILE}):\n{f.read().strip()}")
    if extra:
        parts.append(extra)
    return "\n\n".join(parts)


def remember(workdir, note):
    """Append one note to the project memory file; return a confirmation."""
    path, lead = os.path.join(workdir, MEMORY_FILE), ""
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            text = f.read()
        # A hand-edited file may lack a trailing newline; without this guard
        # the new note would be glued onto the end of the previous line.
        lead = "\n" if text and not text.endswith("\n") else ""
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"{lead}- {' '.join(note.split())}\n")
    return f"Remembered in {MEMORY_FILE}"
