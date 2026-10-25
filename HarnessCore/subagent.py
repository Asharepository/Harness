"""Day 4 -- HarnessCore.subagent: delegating work to a fresh, isolated agent.

Teaches: a sub-agent is just another Harness behind a tool call. The parent
pays one tool result for the whole task; the child's many turns stay in the
child's own context and never inflate the parent's.

Design rules this file embodies:
  - The child starts clean and cannot see the parent's conversation.
  - Depth is bounded, so delegation can never recurse without limit.
"""

from HarnessCore.tools import tool


def subagent_tool(make_harness, depth=0, max_depth=2):
    """Build the spawn_agent Tool; make_harness(depth) must return a new Harness."""

    @tool("Delegate a self-contained task to a fresh sub-agent with its own clean context. "
          "The sub-agent cannot see this conversation, so include everything it needs. "
          "Returns the sub-agent's final report.", task="Complete, self-contained task description")
    def spawn_agent(task):
        if depth >= max_depth:
            return "ERROR: sub-agent depth limit reached; do this task yourself"
        return make_harness(depth + 1).run(task)

    return spawn_agent
