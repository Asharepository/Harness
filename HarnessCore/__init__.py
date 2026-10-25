"""Day 5 -- HarnessCore: a minimal agent harness in the Python standard library.

Teaches: the public surface of the whole week in five names. Everything else
(provider, loop, tools, security, context, memory, skills, session, subagent)
is a part that Harness wires together; most users never import them directly.

Design rules this file embodies:
  - Import cheap, run late: nothing here touches the network or filesystem.
  - The package exports only what a caller needs to build and run an agent.
"""

from HarnessCore.fleet import run_fleet
from HarnessCore.harness import Harness
from HarnessCore.security import Policy
from HarnessCore.tools import Tool, tool

__all__ = ["Harness", "Policy", "Tool", "tool", "run_fleet"]
