import argparse
import json
import sys
from pathlib import Path
from typing import Any

DEFAULT_STORE = Path(__file__).with_name("tasks.json")
VALID_STATUSES = {"todo", "done"}


class TaskmanError(Exception):
    """Raised for user-facing task manager errors."""


class TaskStoreError(TaskmanError):
    """Raised when the JSON task store is invalid."""


class TaskNotFoundError(TaskmanError):
    """Raised when a task id does not exist."""


class TaskValidationError(TaskmanError):
    """Raised when task data or input is invalid."""


Task = dict[str, Any]


def fail(message: str) -> int:
    print(f"Error: {message}", file=sys.stderr)
    return 1


def normalize_title(parts: list[str]) -> str:
    title = " ".join(parts)
    title = " ".join(title.split())
    if not title:
        raise TaskValidationError("task title cannot be empty")
    return title


def validate_task(item: Any, index: int) -> Task:
    if not isinstance(item, dict):
        raise TaskStoreError(f"task {index} is not an object")
    if set(item.keys()) != {"id", "title", "done"}:
        raise TaskStoreError(f"task {index} must contain only id, title, and done")
    task_id = item.get("id")
    title = item.get("title")
    done = item.get("done")
    if not isinstance(task_id, int) or task_id <= 0:
        raise TaskStoreError(f"task {index} has invalid id")
    if not isinstance(title, str) or not title.strip():
        raise TaskStoreError(f"task {index} has invalid title")
    if not isinstance(done, bool):
        raise TaskStoreError(f"task {index} has invalid done flag")
    return {"id": task_id, "title": " ".join(title.split()), "done": done}


def load_tasks(store_path: Path) -> list[Task]:
    if not store_path.exists():
        return []
    try:
        data = json.loads(store_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TaskStoreError(f"could not parse JSON store: {store_path} ({exc.msg})") from exc
    if not isinstance(data, list):
        raise TaskStoreError(f"invalid task store format: {store_path}")
    tasks = [validate_task(item, index + 1) for index, item in enumerate(data)]
    ids = [task["id"] for task in tasks]
    if len(ids) != len(set(ids)):
        raise TaskStoreError(f"duplicate task ids in store: {store_path}")
    return sorted(tasks, key=lambda task: task["id"])


def save_tasks(store_path: Path, tasks: list[Task]) -> None:
    store_path.parent.mkdir(parents=True, exist_ok=True)
    ordered = sorted(tasks, key=lambda task: task["id"])
    store_path.write_text(json.dumps(ordered, indent=2) + "\n", encoding="utf-8")


def next_id(tasks: list[Task]) -> int:
    return max((task["id"] for task in tasks), default=0) + 1


def format_table(tasks: list[Task]) -> str:
    headers = ["ID", "Status", "Task"]
    rows = [[str(task["id"]), "done" if task["done"] else "todo", task["title"]] for task in tasks]
    widths = [len(header) for header in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))
    lines = [
        "  ".join(headers[index].ljust(widths[index]) for index in range(3)).rstrip(),
        "  ".join("-" * widths[index] for index in range(3)),
    ]
    lines.extend("  ".join(row[index].ljust(widths[index]) for index in range(3)).rstrip() for row in rows)
    return "\n".join(lines)


def find_task(tasks: list[Task], task_id: int) -> Task:
    for task in tasks:
        if task["id"] == task_id:
            return task
    raise TaskNotFoundError(f"task {task_id} not found")


def cmd_add(args: argparse.Namespace) -> int:
    tasks = load_tasks(args.store)
    task = {"id": next_id(tasks), "title": normalize_title(args.title), "done": False}
    tasks.append(task)
    save_tasks(args.store, tasks)
    print(f"Added task {task['id']}: {task['title']}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    tasks = load_tasks(args.store)
    if args.status != "all":
        tasks = [task for task in tasks if ("done" if task["done"] else "todo") == args.status]
    if not tasks:
        print(f"No {args.status} tasks found." if args.status != "all" else "No tasks found.")
        return 0
    print(format_table(tasks))
    return 0


def cmd_done(args: argparse.Namespace) -> int:
    tasks = load_tasks(args.store)
    task = find_task(tasks, args.id)
    if task["done"]:
        print(f"Task {args.id} is already done.")
        return 0
    task["done"] = True
    save_tasks(args.store, tasks)
    print(f"Completed task {args.id}: {task['title']}")
    return 0


def cmd_rm(args: argparse.Namespace) -> int:
    tasks = load_tasks(args.store)
    task = find_task(tasks, args.id)
    remaining = [item for item in tasks if item["id"] != args.id]
    save_tasks(args.store, remaining)
    print(f"Removed task {args.id}: {task['title']}")
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    tasks = load_tasks(args.store)
    total = len(tasks)
    done = sum(1 for task in tasks if task["done"])
    todo = total - done
    percent = 0 if total == 0 else round((done / total) * 100)
    print(f"Total:      {total}")
    print(f"Done:       {done}")
    print(f"Todo:       {todo}")
    print(f"Complete:   {percent}%")
    return 0


def positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("task id must be an integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("task id must be positive")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Taskman CLI task manager with JSON persistence.",
        epilog="Examples: taskman.py add Buy milk | taskman.py list --status todo | taskman.py done 2",
    )
    parser.add_argument("--store", type=Path, default=DEFAULT_STORE, help="Path to JSON task store")
    subparsers = parser.add_subparsers(dest="command", required=True, metavar="command")

    add_parser = subparsers.add_parser("add", help="Add a task")
    add_parser.add_argument("title", nargs="+", help="Task title")
    add_parser.set_defaults(func=cmd_add)

    list_parser = subparsers.add_parser("list", help="List tasks")
    list_parser.add_argument("--status", choices=["all", "todo", "done"], default="all", help="Filter by status")
    list_parser.set_defaults(func=cmd_list)

    done_parser = subparsers.add_parser("done", help="Mark a task as done")
    done_parser.add_argument("id", type=positive_int, help="Task ID")
    done_parser.set_defaults(func=cmd_done)

    rm_parser = subparsers.add_parser("rm", help="Remove a task")
    rm_parser.add_argument("id", type=positive_int, help="Task ID")
    rm_parser.set_defaults(func=cmd_rm)

    stats_parser = subparsers.add_parser("stats", help="Show task statistics")
    stats_parser.set_defaults(func=cmd_stats)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except TaskmanError as exc:
        return fail(str(exc))


if __name__ == "__main__":
    sys.exit(main())
