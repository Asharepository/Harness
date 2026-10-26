import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "taskman.py"


class TaskmanCLITests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = Path(self.temp_dir.name) / "tasks.json"

    def tearDown(self):
        self.temp_dir.cleanup()

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--store", str(self.store), *args],
            capture_output=True,
            text=True,
        )

    def seed_store(self, tasks):
        self.store.write_text(json.dumps(tasks, indent=2) + "\n", encoding="utf-8")

    def test_add_creates_store_and_persists_task(self):
        result = self.run_cli("add", "Buy", "milk")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "Added task 1: Buy milk")
        data = json.loads(self.store.read_text(encoding="utf-8"))
        self.assertEqual(data, [{"id": 1, "title": "Buy milk", "done": False}])

    def test_add_multiple_tasks_increments_ids(self):
        self.run_cli("add", "First")
        self.run_cli("add", "Second")
        data = json.loads(self.store.read_text(encoding="utf-8"))
        self.assertEqual([item["id"] for item in data], [1, 2])

    def test_add_normalizes_internal_whitespace(self):
        result = self.run_cli("add", "Plan   ", "   sprint")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "Added task 1: Plan sprint")

    def test_list_empty_store_message(self):
        result = self.run_cli("list")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "No tasks found.")

    def test_list_empty_filtered_message(self):
        result = self.run_cli("list", "--status", "done")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "No done tasks found.")

    def test_list_outputs_aligned_table_without_trailing_padding(self):
        self.run_cli("add", "Short")
        self.run_cli("add", "A", "much", "longer", "task")
        result = self.run_cli("list")
        self.assertEqual(result.returncode, 0)
        lines = result.stdout.strip().splitlines()
        self.assertEqual(lines[0], "ID  Status  Task")
        self.assertEqual(lines[1], "--  ------  ------------------")
        self.assertEqual(lines[2], "1   todo    Short")
        self.assertEqual(lines[3], "2   todo    A much longer task")

    def test_done_marks_task_complete(self):
        self.run_cli("add", "Ship")
        result = self.run_cli("done", "1")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "Completed task 1: Ship")
        data = json.loads(self.store.read_text(encoding="utf-8"))
        self.assertTrue(data[0]["done"])

    def test_done_on_missing_task_fails(self):
        result = self.run_cli("done", "9")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Error: task 9 not found", result.stderr)

    def test_done_twice_is_idempotent(self):
        self.run_cli("add", "Repeat")
        self.run_cli("done", "1")
        result = self.run_cli("done", "1")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "Task 1 is already done.")

    def test_rm_deletes_task(self):
        self.run_cli("add", "One")
        self.run_cli("add", "Two")
        result = self.run_cli("rm", "1")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "Removed task 1: One")
        data = json.loads(self.store.read_text(encoding="utf-8"))
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], 2)

    def test_stats_reports_counts_and_completion_percent(self):
        self.run_cli("add", "One")
        self.run_cli("add", "Two")
        self.run_cli("done", "2")
        result = self.run_cli("stats")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(
            result.stdout.strip().splitlines(),
            ["Total:      2", "Done:       1", "Todo:       1", "Complete:   50%"],
        )

    def test_list_status_filters(self):
        self.run_cli("add", "One")
        self.run_cli("add", "Two")
        self.run_cli("done", "2")
        todo_result = self.run_cli("list", "--status", "todo")
        done_result = self.run_cli("list", "--status", "done")
        self.assertIn("One", todo_result.stdout)
        self.assertNotIn("Two", todo_result.stdout)
        self.assertIn("Two", done_result.stdout)
        self.assertNotIn("One", done_result.stdout)

    def test_invalid_json_store_fails_cleanly(self):
        self.store.write_text("{bad json", encoding="utf-8")
        result = self.run_cli("list")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Error: could not parse JSON store", result.stderr)

    def test_invalid_store_shape_fails_cleanly(self):
        self.store.write_text(json.dumps({"tasks": []}), encoding="utf-8")
        result = self.run_cli("list")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Error: invalid task store format", result.stderr)

    def test_duplicate_ids_in_store_fail_cleanly(self):
        self.seed_store([
            {"id": 1, "title": "One", "done": False},
            {"id": 1, "title": "Two", "done": True},
        ])
        result = self.run_cli("list")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Error: duplicate task ids in store", result.stderr)

    def test_invalid_task_record_fails_cleanly(self):
        self.seed_store([{"id": 0, "title": "Bad", "done": False}])
        result = self.run_cli("list")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Error: task 1 has invalid id", result.stderr)

    def test_negative_id_is_rejected_by_parser(self):
        result = self.run_cli("done", "-1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("task id must be positive", result.stderr)

    def test_help_includes_examples(self):
        result = subprocess.run([sys.executable, str(SCRIPT), "--help"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("Examples:", result.stdout)
        self.assertIn("list --status todo", result.stdout)


if __name__ == "__main__":
    unittest.main()
