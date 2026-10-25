"""Day 5 -- HarnessCore.__main__: lets `python -m HarnessCore` run the CLI.

Teaches: a package becomes runnable with a one-line module that defers to cli.
"""

import sys

from HarnessCore.cli import main

sys.exit(main())
