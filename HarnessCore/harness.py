"""Day 4 -- HarnessCore.harness: the Harness class that composes the week.

Teaches: an agent is the pieces from days 1-4 wired through the loop's
sockets -- provider and loop (day 1), tools and policy (day 2), compaction,
memory and skills (day 3), sessions and sub-agents (day 4). This file adds no
new mechanism; it only decides which piece plugs into which socket.

Design rules this file embodies:
  - Every message is logged the moment it lands, so a kill -9 loses at most
    the call in flight; resume() plus the repair in session.load() continue.
  - Children are ephemeral: a sub-agent never writes a session log, so a
    child's log can never be picked up by resume() as the "latest" session.
  - Compaction shrinks only the live list. The log keeps the full history.
"""

import os

from HarnessCore import context, memory, provider, session, skills
from HarnessCore.loop import run_loop
from HarnessCore.security import Policy
from HarnessCore.subagent import subagent_tool
from HarnessCore.tools import core_tools, tool


class Harness:
    """A ready-to-run agent over one working directory."""

    def __init__(self, workdir=".", model=None, policy=None, extra_tools=None, system_extra="",
                 on_event=None, budget_tokens=600_000, max_turns=120, session_path=None,
                 enable_subagents=True, persist=True, _depth=0):
        """Compose an agent: tools, policy, system prompt and (optionally) a session log.

        model defaults to $HARNESS_MODEL, then provider.DEFAULT_MODEL. policy
        defaults to yolo. extra_tools are merged last, so they can override a
        core tool of the same name. persist=False gives an ephemeral agent
        with no log; _depth is internal bookkeeping for sub-agent recursion.
        """
        self.workdir = os.path.realpath(workdir)
        os.makedirs(self.workdir, exist_ok=True)
        self.model = model or os.environ.get("HARNESS_MODEL") or provider.DEFAULT_MODEL
        self.policy = policy or Policy("yolo")
        self.on_event = on_event or (lambda kind, payload: None)
        self.budget_tokens, self.max_turns = budget_tokens, max_turns
        self.session_path, self.persist = session_path, persist
        self.messages, self._recorded = [], 0
        root = self.workdir

        @tool("Save a durable note to project memory, read at the start of every future session",
              note="The note to remember")
        def remember(note):
            return memory.remember(root, note)

        found = skills.catalog(root)

        @tool("Load a skill's full instructions. They are binding: apply them to your answer",
              name="Skill name from the catalog")
        def use_skill(name):
            return skills.read_skill(root, name)

        def make_child(depth):
            # Same directory and policy, but persist=False: if a child wrote a
            # log it could become the "latest" session and hijack --resume.
            return Harness(root, self.model, self.policy, budget_tokens=budget_tokens,
                           max_turns=max_turns, persist=False, _depth=depth)

        # use_skill exists only when skills do, so the model is never offered
        # a tool whose catalog is empty.
        tools = [*core_tools(root), remember] + ([use_skill] if found else [])
        if enable_subagents:
            tools.append(subagent_tool(make_child, depth=_depth))
        self.tools = {t.name: t for t in tools + list(extra_tools or [])}
        extra = "\n\n".join(p for p in (skills.catalog_prompt(root), system_extra) if p)
        self.system = memory.build_system_prompt(root, extra)

    def resume(self, path=None):
        """Load a session (the latest by default); return True if messages were loaded.

        session.load() has already dropped any torn tail and answered orphaned
        tool calls, so the returned history is always valid provider input.
        """
        path = path or session.latest(self.workdir)
        if not path:
            return False
        self.messages, self.session_path = session.load(path), path
        self._recorded = len(self.messages)
        return bool(self.messages)

    def run(self, task):
        """Run one task to completion, logging every message; return the final text."""
        if self.persist and self.session_path is None:
            self.session_path = session.new_session(self.workdir, task[:32])
        self.messages.append({"role": "user", "text": task})
        self._flush()
        return run_loop(self.model, self.system, self.messages, self.tools, self._event,
                        self.policy.check, self.max_turns, before_turn=self._compact)

    def _flush(self):
        """Append every not-yet-recorded message to the session log."""
        if self.persist and self.session_path:
            for message in self.messages[self._recorded:]:
                session.append(self.session_path, message)
        self._recorded = len(self.messages)

    def _event(self, kind, payload):
        """Record whatever the loop just appended, then forward the event.

        The loop appends each message before emitting its event, so flushing
        on every event logs each message as it lands without touching loop.py.
        """
        self._flush()
        self.on_event(kind, payload)

    def _compact(self, messages):
        """before_turn socket: compact against the budget, keeping the log index valid."""
        self.messages = context.compact(self.model, messages, self.budget_tokens)
        # Compaction shrinks the live list below the recorded count; clamp so
        # the next message to land is still recorded exactly once.
        self._recorded = min(self._recorded, len(self.messages))
        return self.messages
