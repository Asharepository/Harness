# Harness

The smallest agent harness that still does real work: a tool-calling coding
agent in **twelve modules and about 930 lines of Python, with zero
dependencies** (standard library only, Python 3.10+). It gives a model a file
editor, a shell and a search tool inside one directory, keeps long runs inside
a token budget, remembers things between sessions, survives `kill -9`, and can
hand work to sub-agents. It is written to be read: every file opens with the
concept it teaches and the design rules it follows.

## Run it

Set your OpenAI key as an environment variable (or put `OPENAI_API_KEY=...` in
a `.env` file at the repo root; `.env` is gitignored):

```bash
export OPENAI_API_KEY=sk-...        # PowerShell: $env:OPENAI_API_KEY = "sk-..."
```

From the repo root, the three forms:

```bash
python -m HarnessCore                                  # interactive, mode "safe" (asks before changes)
python -m HarnessCore -p "Add tests for utils.py" -d ./myproject   # headless, mode "yolo", exits when done
python -m HarnessCore -d ./myproject --resume          # continue the latest session in that directory
```

Flags: `-p/--prompt`, `-d/--workdir` (default `.`), `-m/--model` (default
`$HARNESS_MODEL`, then `gpt-4o`), `--mode {safe,yolo,read-only}`, `--resume`,
`--max-turns` (default 120). In interactive mode Ctrl-D exits; Ctrl-C
interrupts a run, and the session log (`.harness/sessions/`) is already safe.

**What the jail does and does not do.** The file tools (`read_file`,
`write_file`, `edit_file`, `list_files`, `grep`) refuse any path that resolves
outside the working directory. `bash` runs with that directory as its cwd but
is *not* sandboxed; it is guarded only by the policy's deny patterns (`sudo`,
`rm -rf /`, `curl | sh`, and so on) and by `safe` mode asking you first. Treat
`yolo` as "the model has a shell".

## Anatomy

| Day | Files | Teaches | Lines | Running |
|-----|-------|---------|------:|--------:|
| 1 | `provider.py` `loop.py` | Raw HTTP to the model; the turn loop and its sockets | 176 | 176 |
| 2 | `tools.py` `security.py` | `@tool`, six path-jailed tools; deny rules and the `Policy` gate | 217 | 393 |
| 3 | `context.py` `memory.py` `skills.py` | Compaction under a token budget; durable notes; skills on demand | 155 | 548 |
| 4 | `session.py` `subagent.py` `harness.py` `__init__.py` | Crash-safe logs and repair; delegation; the `Harness` that composes it all | 237 | 785 |
| 5 | `cli.py` `fleet.py` `__main__.py` | The front door; many agents in parallel | 144 | 929 |

Each file plugs into a socket on `loop.run_loop` (`before_tool`, `before_turn`,
`on_event`) rather than modifying it, so later days mostly add files instead
of rewriting earlier ones.

Beside the code: **`Harness.md`** in the working directory is project memory
(appended by the `remember` tool, injected into the system prompt), and
**`skills/<name>/SKILL.md`** adds behavior with no code changes (a
`description:` line in its front matter is what the model sees until it loads
the skill with `use_skill`). `demos/` has a runnable script for each day.

## Compose it

An agent is a `Harness` plus whatever tools you hand it:

```python
from HarnessCore import Harness, tool

@tool("Count the words in a piece of text", text="The text to count")
def word_count(text):
    return str(len(text.split()))

agent = Harness("./myproject", extra_tools=[word_count])
print(agent.run("Use word_count on 'the quick brown fox jumps' and tell me the result."))
```

`@tool` reads the function's signature: parameters without defaults are
required, every parameter is a string, and the keyword arguments describe each
one to the model. Run several agents side by side with `run_fleet`; a job that
fails comes back as a result instead of raising:

```python
from HarnessCore import Harness, run_fleet

jobs = [{"name": "api", "workdir": "./api", "task": "Add a /health endpoint"},
        {"name": "docs", "workdir": "./docs", "task": "Fix broken links"}]
for r in run_fleet(jobs, lambda workdir: Harness(workdir), max_workers=4):
    print(r["name"], "ok" if r["ok"] else "FAILED", "-", r["report"])
```

## License

MIT
