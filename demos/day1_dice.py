"""Day 1 demo: roll_dice proves the loop can drive a hand-written tool.

Run: python demos/day1_dice.py

Prints a full transcript -- user turn, the model's tool call, the tool
result, and the model's final answer -- produced entirely by
HarnessCore.loop.run_loop talking to a single tool with no framework
scaffolding around it, just .spec and .run.
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from HarnessCore import provider
from HarnessCore.loop import run_loop


class RollDice:
    """A hand-written tool: no base class, just the .spec/.run contract."""

    spec = {
        "schema": {
            "name": "roll_dice",
            "description": "Roll count six-sided dice",
            "parameters": {
                "type": "object",
                "properties": {"count": {"type": "string", "description": "How many dice"}},
                "required": ["count"],
            },
        }
    }

    def run(self, count):
        """Roll `count` six-sided dice and return the individual results."""
        return [random.randint(1, 6) for _ in range(int(count))]


def on_event(kind, payload):
    """Print each loop event so the transcript is visible on stdout."""
    if kind == "assistant":
        if payload["text"]:
            print(f"assistant: {payload['text']}")
        for call in payload["tool_calls"]:
            print(f"  tool call: {call['name']}({call['args']})")
    elif kind == "tool_end":
        print(f"  tool result [{payload['name']}]: {payload['text']}")


def before_tool(call):
    """Allow every tool call; day 2 replaces this with real policy."""
    return None


def main():
    task = "Roll 3 dice and tell me whether the total beats 10"
    print(f"user: {task}")
    answer = run_loop(
        provider.DEFAULT_MODEL,
        "You are a terse assistant with access to a dice-rolling tool.",
        [{"role": "user", "text": task}],
        {"roll_dice": RollDice()},
        on_event,
        before_tool,
    )
    print(f"final: {answer}")


if __name__ == "__main__":
    main()
