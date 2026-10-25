"""Day 3 demo: durable memory and skills, with zero changes to harness code.

Run: python demos/day3_memory_skills.py memory
     python demos/day3_memory_skills.py skills

memory: remember() a fact, then ask about it in a brand-new conversation. The
        answer must come from the system prompt alone (no tool calls).
skills: run one writing task before and after dropping skills/brand-voice/
        SKILL.md into the directory. Only a data file changes between runs.
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from HarnessCore import provider
from HarnessCore.loop import run_loop
from HarnessCore.memory import MEMORY_FILE, build_system_prompt, remember
from HarnessCore.security import Policy
from HarnessCore.skills import SKILLS_DIR, catalog_prompt, read_skill
from HarnessCore.tools import core_tools, tool

WRITING_TASK = "Write a two-sentence welcome message for our coffee shop's website."
SKILL_MD = """---
name: brand-voice
description: Voice and tone for any writing or copy task (messages, taglines, announcements)
---
Write everything in pirate speak: "Ahoy", "matey", "ye", "me hearty", "aye".
Keep it friendly and short. Never break character.
"""


def converse(workdir, question, label):
    """Run one fresh conversation over workdir; return (answer, tool calls made)."""
    workdir = str(workdir)
    calls = []

    @tool("Load the full instructions of a named skill", name="Skill name from the catalog")
    def use_skill(name):
        return read_skill(workdir, name)

    tools = {t.name: t for t in core_tools(workdir) + [use_skill]}
    rule = "Instructions returned by use_skill are binding: apply them to your final answer."
    catalog = catalog_prompt(workdir)
    system = build_system_prompt(workdir, extra=f"{catalog}\n{rule}" if catalog else "")

    def on_event(kind, payload):
        if kind == "tool_start":
            calls.append(payload["name"])
            print(f"  tool call: {payload['name']}({payload['args']})")

    answer = run_loop(provider.DEFAULT_MODEL, system, [{"role": "user", "text": question}],
                      tools, on_event, Policy("yolo").check)
    print(f"[{label}] {answer}\n[{label}] tool calls: {calls or 'none'}\n")
    return answer, calls


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "memory"
    scratch = Path(tempfile.mkdtemp(prefix="harness_demo_"))
    print(f"directory: {scratch}")
    if mode == "memory":
        print(remember(str(scratch), "The deploy codename for this project is Bluefin-7."))
        print(f"--- {MEMORY_FILE} ---\n{(scratch / MEMORY_FILE).read_text()}")
        converse(scratch, "What is the deploy codename for this project?", "fresh conversation")
    else:
        converse(scratch, WRITING_TASK, "no skill")
        (scratch / SKILLS_DIR / "brand-voice").mkdir(parents=True)
        (scratch / SKILLS_DIR / "brand-voice" / "SKILL.md").write_text(SKILL_MD, encoding="utf-8")
        converse(scratch, WRITING_TASK, "with brand-voice skill")


if __name__ == "__main__":
    main()
