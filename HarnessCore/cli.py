"""Day 4 -- HarnessCore.cli: the command-line entry point (a stub until day 5).

Teaches: `python -m HarnessCore` should reach the Harness through one small
function, so the entry point stays thin and the logic stays importable.

Design rules this file embodies:
  - main() takes no arguments and returns an exit code; __main__ owns exit.
"""


def main():
    """Entry point for `python -m HarnessCore`; day 5 adds the real interface."""
    print("HarnessCore: the command-line interface arrives on day 5.")
    print("For now: from HarnessCore import Harness; Harness('.').run('your task')")
    return 0
