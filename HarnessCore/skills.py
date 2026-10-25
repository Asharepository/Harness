"""Day 3 -- HarnessCore.skills: new behavior from a folder, not a code change.

Teaches: a skill is a markdown file the model loads on demand. Only a short
catalog sits in the system prompt; full instructions arrive through a tool
call, so many skills cost almost nothing until used.

Design rules this file embodies:
  - A skill is skills/<name>/SKILL.md; dropping one in changes behavior with
    zero edits to harness code.
  - Descriptions are always visible, bodies load on demand.
  - A bad skill name fails soft, as a result the model can read and correct.
"""

import os

SKILLS_DIR = "skills"


def _description(text):
    """Return the `description:` line from front matter, or "" when absent."""
    lines = text.splitlines()
    for line in lines[1:] if lines and lines[0].strip() == "---" else []:
        if line.strip() == "---":
            break
        if line.startswith("description:"):
            return line.split(":", 1)[1].strip()
    return ""


def catalog(workdir):
    """Return {name: {"description", "path"}} for every skills/<name>/SKILL.md."""
    root, found = os.path.join(workdir, SKILLS_DIR), {}
    for name in sorted(os.listdir(root)) if os.path.isdir(root) else []:
        path = os.path.join(root, name, "SKILL.md")
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                found[name] = {"description": _description(f.read()), "path": path}
    return found


def catalog_prompt(workdir):
    """Render the catalog for the system prompt ("" when there are no skills)."""
    skills = catalog(workdir)
    if not skills:
        return ""
    header = "Skills available (load one with the use_skill tool when relevant):"
    return "\n".join([header] + [f"- {name}: {s['description']}" for name, s in skills.items()])


def read_skill(workdir, name):
    """Return a skill's full SKILL.md text, or an ERROR string on a miss."""
    skills = catalog(workdir)
    if name not in skills:
        return f"ERROR: no skill named {name}. Available: {', '.join(skills) or '(none)'}"
    with open(skills[name]["path"], encoding="utf-8") as f:
        return f.read()
