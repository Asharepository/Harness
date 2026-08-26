"""Day 1 -- HarnessCore.loop: the turn loop that drives model and tools.

Teaches: the boundary between "the model decided to act" and "the action
happened" -- the loop calls the provider, then executes whatever tool calls
came back, one at a time, and feeds each result back in as its own message.

Design rules this file embodies:
  - A tool that raises never takes the loop down with it; the exception
    becomes the tool's result text and the conversation continues.
  - on_event is the only introspection point -- nothing here prints or
    logs directly, so the loop is equally usable headless or interactive.
  - before_tool is the sole security gate: it runs before every call, and a
    non-None return blocks execution. Day 2 gives it real policy; today it
    always allows.
  - before_turn can rewrite the message list before each model call, but
    does nothing yet -- day 3 plugs context compaction in here.
"""

from HarnessCore import provider


def run_loop(model, system, messages, tools, on_event, before_tool, max_turns=80, before_turn=None):
    """Drive the model/tool turn loop to completion; return the final text."""
    for _ in range(max_turns):
        if before_turn is not None:
            messages = before_turn(messages)

        result = provider.complete(model, system, messages, [t.spec for t in tools.values()])
        messages.append({"role": "assistant", "text": result["text"], "tool_calls": result["tool_calls"]})
        on_event("assistant", result)

        if not result["tool_calls"]:
            return result["text"]

        for call in result["tool_calls"]:
            on_event("tool_start", call)
            text = _run_tool(tools, call, before_tool)
            messages.append({"role": "tool", "name": call["name"], "text": text})
            on_event("tool_end", {"name": call["name"], "text": text})

    messages.append({"role": "user", "text": "Turn limit reached; wrap up now."})
    result = provider.complete(model, system, messages, None)
    messages.append({"role": "assistant", "text": result["text"], "tool_calls": result["tool_calls"]})
    on_event("assistant", result)
    return result["text"]


def _run_tool(tools, call, before_tool):
    """Execute one tool call, translating blocks/errors into result text."""
    reason = before_tool(call)
    if reason is not None:
        return f"BLOCKED: {reason}"

    tool = tools.get(call["name"])
    if tool is None:
        return f"ERROR: unknown tool {call['name']}"

    try:
        return str(tool.run(**call["args"]))
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"
