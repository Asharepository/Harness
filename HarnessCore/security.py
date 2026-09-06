"""Day 2 -- HarnessCore.security: the before_tool gate that loop.py calls.

Teaches: security policy lives in one small, model-independent place -- a
Policy is handed to run_loop as before_tool and never touches the model or
the tools themselves. It only ever sees the call the model wants to make.

Design rules this file embodies:
  - Deny patterns are checked before mode, before everything: no mode,
    including yolo, can talk a policy into running a destructive command.
  - Read-only tools are always allowed, in every mode, because they can't
    change anything the deny patterns need to protect.
  - "safe" mode's default approver refuses by default -- an unwired policy
    fails closed, not open.
"""

import re

READ_TOOLS = {"read_file", "list_files", "grep"}

DENY_PATTERNS = [
    r"rm\s+-[a-zA-Z-]*r[a-zA-Z-]*f[a-zA-Z-]*\s+(/|~|\$HOME)(\s|/|$)",
    r"rm\s+-[a-zA-Z-]*f[a-zA-Z-]*r[a-zA-Z-]*\s+(/|~|\$HOME)(\s|/|$)",
    r"\bsudo\b",
    r"\bmkfs\b",
    r"\bdd\s+if=",
    r"curl\s[^|]*\|\s*(sudo\s+)?(sh|bash)\b",
    r"git\s+push\s+.*--force\b",
    r">\s*/dev/sd[a-z]\d*\b",
]


class Policy:
    """The tool-call gate: mode is one of "read-only", "safe", "yolo"."""

    def __init__(self, mode="safe", approver=None):
        self.mode = mode
        self.approver = approver or (lambda call, reason: False)

    def check(self, call):
        """Return None to allow a call, or a reason string to block it."""
        if call["name"] == "bash":
            command = call["args"].get("command", "")
            for pattern in DENY_PATTERNS:
                if re.search(pattern, command, re.IGNORECASE):
                    return f"command matches a denied pattern: {pattern}"

        if call["name"] in READ_TOOLS or self.mode == "yolo":
            return None

        if self.mode == "read-only":
            return f"read-only mode blocks {call['name']}"

        reason = f"approve {call['name']}({call['args']})?"
        if self.approver(call, reason):
            return None
        return f"not approved: {call['name']}"
