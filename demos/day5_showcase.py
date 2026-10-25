"""Day 5 showcase: build three products with the harness itself, via run_fleet.

Run: python demos/day5_showcase.py [root]      (root defaults to ./projects)

Each project gets a fresh directory holding the design-engineering skill. Phase
1 builds it; phase 2 resumes the same session (Harness.resume) for a demanding
design-director review. Verification afterwards is mechanical and independent
of the model: files, a real test run, greps and a visible-word count. A project
that falls short gets one more review pass, never a lowered bar.
"""

import re
import subprocess
import sys
import time
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from HarnessCore import Harness, run_fleet

BAR = (
    "a real design system as CSS custom properties; at least 9 distinct sections for a landing "
    "page; at least 1,200 words of real copy, no lorem ipsum; at least 4 hand-drawn inline SVG "
    "illustrations, one being a product artifact in the hero; at least 3 working interactive "
    "behaviors; responsive at 360, 768, and 1280; semantic HTML with focus states; a self-review "
    "pass before finishing that counts sections, words, SVGs, and interactions against these "
    "minimums and fixes any shortfall."
)
SKILL = (
    "---\nname: design-engineering\ndescription: Quality bar for any product build "
    "(design system, copy, SVG, interactivity, responsiveness, self-review). Load it before building.\n---\n"
    f"# Design engineering quality bar\n\nThe bar: {BAR}\n"
)
SYSTEM_EXTRA = (
    "Environment notes: the shell is Windows cmd, so avoid unix-only commands (wc, grep, head); run "
    "Python as `python`. Each response has a hard output limit, so never put more than about 150 "
    "lines (8,000 characters) in a single write_file or edit_file call: for a large file, write a "
    "skeleton containing marker comments, then fill each marker with edit_file, one section at a "
    "time. When a task says one file or self-contained, keep everything (HTML, CSS, JS) in that one "
    "file. Verify counts (words, sections, SVGs) with small `python` scripts, not by eye."
)
PREFIX = "First load the design-engineering skill with use_skill and follow its quality bar. "
REVIEW = ("Review every file you produced against the skill bar as a demanding design director; "
          "list 12 concrete deficiencies; fix them all; verify again.")
TASKS = {
    "artisan-coffee": PREFIX + "Build artisan-coffee: a self-contained index.html for a specialty "
        "coffee roaster in Goa -- sticky nav, hero with a drawn product artifact, six origin cards "
        "with prices, a three-tier subscription table with a working monthly/annual toggle, brew-guide "
        "tabs, an FAQ accordion, a dark-mode toggle persisted to localStorage.",
    "taskman": PREFIX + "Build taskman: a python CLI task manager in taskman.py -- argparse "
        "subcommands add, list, done, rm, stats; JSON persistence; aligned table output; and "
        "test_taskman.py, a unittest suite of 10+ cases run via subprocess against a temp store; all "
        "tests green. (The skill's CSS/SVG/landing-page counts do not apply to a CLI; apply its "
        "self-review discipline and verify mechanically.)",
    "viper": PREFIX + "Build viper: a canvas snake game in one index.html -- grid movement on "
        "requestAnimationFrame, food, speed-up every 5 foods, score, pause, restart, high score in "
        "localStorage. (The skill's landing-page section/word counts do not apply to a game; apply "
        "its design tokens, responsiveness, semantic HTML, focus states and self-review.)",
}


class _Text(HTMLParser):
    """Collect visible text, skipping script, style and svg content."""

    def __init__(self):
        super().__init__()
        self.skip, self.chunks = 0, []

    def handle_starttag(self, tag, attrs):
        self.skip += tag in ("script", "style", "svg", "noscript", "template")

    def handle_endtag(self, tag):
        self.skip -= tag in ("script", "style", "svg", "noscript", "template")

    def handle_data(self, data):
        if not self.skip:
            self.chunks.append(data)


def visible_words(html):
    parser = _Text()
    parser.feed(html)
    return len(re.findall(r"[A-Za-z0-9'’-]+", " ".join(parser.chunks)))


def verify(name, root):
    """Return (passed, notes) from mechanical checks on one project directory."""
    d, notes, ok = root / name, [], True

    def check(label, cond, detail=""):
        nonlocal ok
        ok &= bool(cond)
        notes.append(f"{'PASS' if cond else 'FAIL'} {label} {detail}".strip())

    read = lambda f: (d / f).read_text(encoding="utf-8", errors="replace") if (d / f).is_file() else ""
    if name == "taskman":
        check("taskman.py exists", (d / "taskman.py").is_file())
        check("test_taskman.py exists", (d / "test_taskman.py").is_file())
        r = subprocess.run([sys.executable, "-m", "unittest", "test_taskman"], cwd=d, capture_output=True, text=True)
        n = re.search(r"Ran (\d+) tests?", r.stderr)
        check("unittest green", r.returncode == 0, f"({n.group(0) if n else r.stderr[-120:]})")
        check(">=10 tests", n and int(n.group(1)) >= 10)
        check("tests use subprocess", "subprocess" in read("test_taskman.py"))
        h = subprocess.run([sys.executable, "taskman.py", "-h"], cwd=d, capture_output=True, text=True).stdout
        check("subcommands in --help", all(c in h for c in ("add", "list", "done", "rm", "stats")))
    else:
        html = read("index.html")
        check("index.html exists", bool(html), f"({len(html)} chars)")
        if name == "viper":
            check("requestAnimationFrame", "requestAnimationFrame" in html)
            for word in ("<canvas", "localStorage", "pause"):
                check(f"has {word}", word.lower() in html.lower())
            check("restart control", re.search(r"restart|play again|new game", html, re.I))
        else:
            words, svgs = visible_words(html), len(re.findall(r"<svg\b", html))
            sections = len(re.findall(r"<section\b", html))
            check("localStorage", "localStorage" in html)
            check("accordion", re.search(r"accordion|<details|aria-expanded", html, re.I))
            check("visible words > 1200", words > 1200, f"({words})")
            check("sections >= 9", sections >= 9, f"({sections})")
            check("inline SVG >= 4", svgs >= 4, f"({svgs})")
            check("no lorem ipsum", "lorem" not in html.lower())
            check("CSS custom properties", len(re.findall(r"--[\w-]+\s*:", html)) >= 10)
            check("@media queries", "@media" in html)
            check(":focus styles", ":focus" in html)
            check("interactions >= 3", len(re.findall(r"addEventListener|onclick", html)) >= 3)
    return ok, notes


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "projects").resolve()
    started, harnesses = time.time(), {}

    def make(workdir, resume):
        name = Path(workdir).name

        def log(kind, payload):
            line = {"assistant": lambda: (payload["text"] or "")[:100].replace("\n", " "),
                    "tool_start": lambda: f"-> {payload['name']} {str(payload['args'])[:70]}",
                    "tool_end": lambda: f"   {payload['text'][:80]!r}"}.get(kind, lambda: None)()
            if line is not None:
                with open(root / f"{name}.events.log", "a", encoding="utf-8") as f:
                    f.write(f"{time.time() - started:7.0f}s {kind:10} {line}\n")

        h = Harness(workdir, budget_tokens=60_000, system_extra=SYSTEM_EXTRA, on_event=log)
        if resume:
            h.resume()
        harnesses[name] = h
        return h

    jobs = []
    for name, task in TASKS.items():
        workdir = root / name
        (workdir / "skills" / "design-engineering").mkdir(parents=True)  # fresh: fails if it exists
        (workdir / "skills" / "design-engineering" / "SKILL.md").write_text(SKILL, encoding="utf-8")
        jobs.append({"name": name, "workdir": str(workdir), "task": task})

    turns, reports = {}, {}
    phases = [("build", TASKS, False), ("review", {n: REVIEW for n in TASKS}, True)]
    for phase, tasks, resume in phases:
        phase_jobs = [{**j, "task": tasks[j["name"]]} for j in jobs]
        print(f"=== phase: {phase} ===", flush=True)
        for r in run_fleet(phase_jobs, lambda wd, _r=resume: make(wd, _r), max_workers=3):
            reports[(r["name"], phase)] = r
            asst = sum(m["role"] == "assistant" for m in harnesses[r["name"]].messages)
            turns[(r["name"], phase)] = asst - turns.get((r["name"], "build"), 0) if phase == "review" else asst
            print(f"{r['name']:15} {phase:7} ok={r['ok']} turns={turns[(r['name'], phase)]}", flush=True)

    results = {}
    for name in TASKS:
        ok, notes = verify(name, root)
        if not ok:  # one more review pass, never a lowered bar
            shortfalls = "; ".join(n for n in notes if n.startswith("FAIL"))
            print(f"--- {name} short ({shortfalls}); one more review pass ---", flush=True)
            run_fleet([{"name": name, "workdir": str(root / name),
                        "task": REVIEW + " Mechanical checks just failed: " + shortfalls}],
                      lambda wd: make(wd, True), max_workers=1)
            turns[(name, "extra")] = sum(m["role"] == "assistant" for m in harnesses[name].messages) - turns[(name, "build")] - turns[(name, "review")]
            ok, notes = verify(name, root)
        results[name] = (ok, notes)

    lines = ["| project | result | turns (build+review[+extra]) | notes |", "|---|---|---|---|"]
    for name, (ok, notes) in results.items():
        t = "+".join(str(turns.get((name, p), 0)) for p in ("build", "review") + (("extra",) if (name, "extra") in turns else ()))
        lines.append(f"| {name} | {'PASS' if ok else 'FAIL'} | {t} | {'; '.join(n for n in notes)} |")
    (root / "RESULTS.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n" + "\n".join(lines))
    print(f"\nelapsed: {(time.time() - started) / 60:.1f} min")


if __name__ == "__main__":
    main()
