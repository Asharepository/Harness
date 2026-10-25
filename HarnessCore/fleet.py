"""Day 5 -- HarnessCore.fleet: many independent agents, run side by side.

Teaches: because a Harness owns one directory and shares nothing, running a
fleet is just running Harnesses in threads. The work is I/O (waiting on the
model), so threads are enough and no coordination code is needed.

Design rules this file embodies:
  - One job, one Harness, one directory: jobs cannot interfere.
  - A failing job is a result, not an exception: one bad job never costs the
    reports of the others.
"""

from concurrent.futures import ThreadPoolExecutor


def run_fleet(jobs, make_harness, max_workers=4):
    """Run [{name, workdir, task}] jobs in parallel; return reports in input order.

    make_harness(workdir) must return a fresh Harness for each call, since
    Harness objects hold a conversation and must never be shared across jobs.
    Each result is {"name", "ok", "report"}: the final text, or "<type>: <message>".
    """

    def run_one(job):
        # Exception, not BaseException: Ctrl-C must still stop the whole fleet.
        try:
            report = make_harness(job["workdir"]).run(job["task"])
            return {"name": job["name"], "ok": True, "report": report}
        except Exception as e:
            return {"name": job["name"], "ok": False, "report": f"{type(e).__name__}: {e}"}

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        return list(pool.map(run_one, jobs))  # map preserves input order
