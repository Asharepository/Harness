import argparse
import json
import os

TASKS_FILE = 'tasks.json'

# Ensure tasks file exists
if not os.path.exists(TASKS_FILE):
    with open(TASKS_FILE, 'w') as f:
        json.dump([], f)

# Load tasks from the JSON file
def load_tasks():
    with open(TASKS_FILE, 'r') as f:
        return json.load(f)

# Save tasks to the JSON file
def save_tasks(tasks):
    with open(TASKS_FILE, 'w') as f:
        json.dump(tasks, f, indent=4)

# Add a new task
def add_task(description, priority='medium', due_date=None):
    if not description:
        print("Error: Task description cannot be empty.")
        return
    tasks = load_tasks()
    tasks.append({'description': description, 'done': False, 'priority': priority, 'due_date': due_date})
    save_tasks(tasks)
    print(f"Task added: {description}")

# List all tasks
def list_tasks(sort_by=None):
    tasks = load_tasks()
    if sort_by == 'priority':
        tasks.sort(key=lambda x: x['priority'])
    elif sort_by == 'due_date':
        tasks.sort(key=lambda x: x['due_date'] or '')
    for i, task in enumerate(tasks, start=1):
        status = 'Done' if task['done'] else 'Pending'
        print(f"{i}. [{status}] {task['description']} (Priority: {task['priority']}, Due: {task['due_date']})")

# Mark a task as done
def mark_done(index):
    tasks = load_tasks()
    if 0 <= index < len(tasks):
        tasks[index]['done'] = True
        save_tasks(tasks)
        message = f"Task {index + 1} marked as done."
        print(message)
        return message
    else:
        error_message = "Error: Invalid task index."
        print(error_message)
        return error_message

# Remove a task
def remove_task(index):
    tasks = load_tasks()
    if 0 <= index < len(tasks):
        confirm = input(f"Are you sure you want to remove task {index + 1}? (y/n): ")
        if confirm.lower() == 'y':
            tasks.pop(index)
            save_tasks(tasks)
            print("Task removed.")
            return "Task removed."
        else:
            print("Task not removed.")
            return "Task not removed."
    else:
        print("Error: Invalid task index.")
        return "Error: Invalid task index."
    tasks = load_tasks()
    if 0 <= index < len(tasks):
        confirm = input(f"Are you sure you want to remove task {index + 1}? (y/n): ")
        if confirm.lower() == 'y':
            tasks.pop(index)
            save_tasks(tasks)
            print("Task removed.")
        else:
            print("Task not removed.")
    else:
        print("Error: Invalid task index.")

# Show task statistics
def show_stats():
    tasks = load_tasks()
    total = len(tasks)
    done = sum(task['done'] for task in tasks)
    pending = total - done
    print(f"Total: {total}, Done: {done}, Pending: {pending}")
    if pending > 0:
        pending_tasks = [task for task in tasks if not task['done']]
        highest_priority = min(pending_tasks, key=lambda x: x['priority'])['priority']
        print(f"Highest priority pending task: {highest_priority}")

# Main function to handle command line arguments
def main():
    parser = argparse.ArgumentParser(description='Task Manager')
    subparsers = parser.add_subparsers(dest='command')

    # Add task command
    parser_add = subparsers.add_parser('add', help='Add a new task')
    parser_add.add_argument('description', type=str, help='Description of the task')
    parser_add.add_argument('--priority', type=str, choices=['low', 'medium', 'high'], default='medium', help='Priority of the task')
    parser_add.add_argument('--due', type=str, help='Due date of the task')

    # List tasks command
    parser_list = subparsers.add_parser('list', help='List all tasks')
    parser_list.add_argument('--sort', type=str, choices=['priority', 'due_date'], help='Sort tasks by')

    # Mark task as done command
    parser_done = subparsers.add_parser('done', help='Mark a task as done')
    parser_done.add_argument('index', type=int, help='Index of the task to mark as done')

    # Remove task command
    parser_rm = subparsers.add_parser('rm', help='Remove a task')
    parser_rm.add_argument('index', type=int, help='Index of the task to remove')

    # Show stats command
    parser_stats = subparsers.add_parser('stats', help='Show task statistics')

    args = parser.parse_args()

    if args.command == 'add':
        add_task(args.description, args.priority, args.due)
    elif args.command == 'list':
        list_tasks(args.sort)
    elif args.command == 'done':
        mark_done(args.index - 1)
    elif args.command == 'rm':
        remove_task(args.index - 1)
    elif args.command == 'stats':
        show_stats()

if __name__ == '__main__':
    main()
