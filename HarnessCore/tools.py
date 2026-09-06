"""Day 2 -- HarnessCore.tools: turning plain functions into model-callable tools.

Teaches: a Tool is just a name, a schema, and a callable -- nothing about the
provider or the loop needs to change to support new capabilities. The six
core tools give a model a sandboxed view of one directory: everything it can
touch is reachable only through resolve(), so "escape the workdir" is a single
choke point instead of six places that could each get it wrong.

Design rules this file embodies:
  - The tool() decorator infers a JSON schema from a function's own
    signature, so the schema can never drift out of sync with the code.
  - Every path argument passes through resolve() before it touches the
    filesystem; there is no tool-specific path handling anywhere below.
  - A tool's failure mode is its return value, not an exception -- callers
    (the loop) should never need a try/except around tool.run().
"""

import fnmatch
import inspect
import os
import re
import subprocess
from dataclasses import dataclass
from typing import Callable

_IGNORE = {".git", "node_modules", "__pycache__", ".venv"}


@dataclass
class Tool:
    """A model-callable tool: its name, its provider-facing schema, and the code it runs."""

    name: str
    spec: dict
    run: Callable


def tool(description, **params):
    """Decorate a function into a Tool, inferring its schema from its signature.

    Parameters with defaults become optional in the schema; every parameter
    is typed as a string on purpose, since that's all a model ever sends.
    """

    def decorator(fn):
        sig = inspect.signature(fn)
        properties = {name: {"type": "string", "description": params[name]} for name in sig.parameters}
        required = [name for name, p in sig.parameters.items() if p.default is inspect.Parameter.empty]
        schema = {
            "name": fn.__name__,
            "description": description,
            "parameters": {"type": "object", "properties": properties, "required": required},
        }
        return Tool(name=fn.__name__, spec={"schema": schema}, run=fn)

    return decorator


def core_tools(workdir):
    """Build the six filesystem/shell tools, sandboxed to the real path of workdir."""
    root = os.path.realpath(workdir)

    def resolve(path):
        # The single choke point every path argument passes through: resolve
        # symlinks too, so a link inside workdir can't point an escape hatch
        # outside it.
        full = os.path.realpath(os.path.join(root, path))
        if full != root and not full.startswith(root + os.sep):
            raise PermissionError(f"{path!r} escapes the working directory")
        return full

    @tool("Read a file's contents with line numbers", path="Path to the file")
    def read_file(path):
        with open(resolve(path), encoding="utf-8") as f:
            lines = f.read().splitlines()
        total = len(lines)
        shown = lines[:4000]
        text = "\n".join(f"{i}\t{line}" for i, line in enumerate(shown, 1))
        if total > 4000:
            text += f"\n... truncated, {total} lines total"
        return text

    @tool("Write content to a file, creating parent directories as needed",
          path="Path to the file", content="The text to write")
    def write_file(path, content):
        full = resolve(path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Wrote {len(content)} chars to {path}"

    @tool("Replace one exact snippet of a file's contents with new text",
          path="Path to the file", old="Exact text to replace", new="Replacement text")
    def edit_file(path, old, new):
        full = resolve(path)
        with open(full, encoding="utf-8") as f:
            content = f.read()
        # The snippet must be unique: on zero matches the model probably
        # misquoted the file, on multiple matches a partial replace would be
        # ambiguous, so both are refused rather than guessed at.
        count = content.count(old)
        if count == 0:
            return "ERROR: snippet not found — read the file and copy it exactly"
        if count > 1:
            return f"ERROR: snippet appears {count} times — include more context to make it unique"
        with open(full, "w", encoding="utf-8") as f:
            f.write(content.replace(old, new, 1))
        return f"Edited {path}"

    @tool("Run a shell command in the working directory",
          command="The shell command to run", timeout="Timeout in seconds")
    def bash(command, timeout="120"):
        t = int(timeout)
        try:
            proc = subprocess.run(command, shell=True, cwd=root, capture_output=True, text=True, timeout=t)
        except subprocess.TimeoutExpired:
            return f"ERROR: timed out after {t}s"
        output = proc.stdout + proc.stderr
        if len(output) > 12000:
            output = output[:6000] + "\n...[truncated]...\n" + output[-6000:]
        return output if output else f"(exit {proc.returncode}, no output)"

    @tool("List files under the working directory matching a glob pattern",
          pattern="Glob pattern to match against relative path or filename")
    def list_files(pattern="**/*"):
        matches = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in _IGNORE]
            for name in filenames:
                rel = os.path.relpath(os.path.join(dirpath, name), root)
                if fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(name, pattern):
                    matches.append(rel)
        matches.sort()
        text = "\n".join(matches[:500])
        if len(matches) > 500:
            text += f"\n... and {len(matches) - 500} more"
        return text

    @tool("Search file contents for a regex, line by line",
          regex="Regular expression to search for", pattern="Glob pattern filtering which files to search")
    def grep(regex, pattern="*"):
        compiled = re.compile(regex)
        hits = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in _IGNORE]
            for name in filenames:
                rel = os.path.relpath(os.path.join(dirpath, name), root)
                if not (fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(name, pattern)):
                    continue
                try:
                    with open(os.path.join(dirpath, name), encoding="utf-8") as f:
                        for lineno, line in enumerate(f, 1):
                            if compiled.search(line):
                                hits.append(f"{rel}:{lineno}: {line.rstrip(chr(10))[:200]}")
                                if len(hits) >= 200:
                                    return "\n".join(hits)
                except (UnicodeDecodeError, OSError):
                    continue
        return "\n".join(hits)

    return [read_file, write_file, edit_file, bash, list_files, grep]
