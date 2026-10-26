import unittest
import subprocess
import os
import json

class TestTaskman(unittest.TestCase):
    TASKS_FILE = 'tasks.json'

    def setUp(self):
        # Backup and clear the tasks file
        if os.path.exists(self.TASKS_FILE):
            if os.path.exists(self.TASKS_FILE + '.bak'):
                os.remove(self.TASKS_FILE + '.bak')
        
        os.rename(self.TASKS_FILE, self.TASKS_FILE + '.bak')
        with open(self.TASKS_FILE, 'w') as f:
            json.dump([], f)

    def tearDown(self):
        # Restore the tasks file
        if os.path.exists(self.TASKS_FILE + '.bak'):
            if os.path.exists(self.TASKS_FILE):
                os.remove(self.TASKS_FILE)
        os.rename(self.TASKS_FILE + '.bak', self.TASKS_FILE)

    def run_cli(self, *args, input_text=None):
        result = subprocess.run(['python', 'taskman.py'] + list(args), capture_output=True, text=True, input=input_text)
        return result.stdout.strip()

    def test_add_task(self):
        self.run_cli('add', 'Test Task 1', '--priority', 'high', '--due', '2023-12-31')
        output = self.run_cli('list')
        self.assertIn('Test Task 1', output)
        self.assertIn('Priority: high', output)
        self.assertIn('Due: 2023-12-31', output)

    def test_list_tasks(self):
        self.run_cli('add', 'Test Task 2', '--priority', 'low')
        output = self.run_cli('list', '--sort', 'priority')
        self.assertIn('Test Task 2', output)
        self.assertIn('Priority: low', output)

    def test_mark_done(self):
        self.run_cli('add', 'Test Task 3')
        self.run_cli('done', '1')
        output = self.run_cli('list')
        self.assertIn('[Done] Test Task 3', output)
        # self.assertIn('Task 1 marked as done.', output)

    def test_remove_task(self):
        self.run_cli('add', 'Test Task 4')
        self.run_cli('rm', '1', input_text='y\n')
        output = self.run_cli('list')
        self.assertNotIn('Test Task 4', output)

    def test_show_stats(self):
        self.run_cli('add', 'Test Task 5')
        self.run_cli('done', '1')
        output = self.run_cli('stats')
        self.assertIn('Total: 1, Done: 1, Pending: 0', output)

    def test_add_multiple_tasks(self):
        self.run_cli('add', 'Task 1')
        self.run_cli('add', 'Task 2')
        output = self.run_cli('list')
        self.assertIn('Task 1', output)
        self.assertIn('Task 2', output)

    def test_mark_multiple_done(self):
        self.run_cli('add', 'Task 1')
        self.run_cli('add', 'Task 2')
        self.run_cli('done', '1')
        self.run_cli('done', '2')
        output = self.run_cli('list')
        self.assertIn('[Done] Task 1', output)
        self.assertIn('[Done] Task 2', output)

    def test_remove_multiple_tasks(self):
        self.run_cli('add', 'Task 1')
        self.run_cli('add', 'Task 2')
        self.run_cli('rm', '1', input_text='y\n')
        self.run_cli('rm', '1', input_text='y\n')
        output = self.run_cli('list')
        self.assertNotIn('Task 1', output)
        self.assertNotIn('Task 2', output)

    def test_stats_with_no_tasks(self):
        output = self.run_cli('stats')
        self.assertIn('Total: 0, Done: 0, Pending: 0', output)

    def test_list_with_no_tasks(self):
        output = self.run_cli('list')
        self.assertEqual(output, '')

if __name__ == '__main__':
    unittest.main()
