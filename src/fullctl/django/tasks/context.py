"""
Task execution context management.

Provides a thread-safe way to access the currently executing task
from anywhere in the call stack without explicit parameter passing.
"""

from contextvars import ContextVar
from typing import Optional

__all__ = [
    "task_execution_context",
    "get_current_task",
    "check_task_cancelled",
]

_current_task: ContextVar = ContextVar("current_task", default=None)


class task_execution_context:
    """
    Context manager for tracking the currently executing task.

    This sets the task in context-local storage, making it accessible
    to any code in the call stack via get_current_task() without
    requiring explicit parameter passing.

    Usage:
        with task_execution_context(task):
            # task is now accessible via get_current_task()
            do_work()

    Example:
        class MyTask(Task):
            def run(self, *args, **kwargs):
                # Context automatically set by Task._run()
                process_data()  # Can call check_task_cancelled() anywhere

    Note:
        In most cases, you don't need to use this directly.
        Task._run() automatically wraps execution in this context.
    """

    def __init__(self, task):
        """
        Initialize context manager.

        Args:
            task: The Task instance to set as current
        """
        self.task = task
        self.token = None

    def __enter__(self):
        """
        Enter the context and set current task.

        Returns:
            The task instance
        """
        # Set the task and get a token for cleanup
        self.token = _current_task.set(self.task)
        return self.task

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit the context and restore previous task.

        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred

        Returns:
            False to propagate exceptions (don't suppress)
        """
        # Reset to previous value using the token
        _current_task.reset(self.token)
        return False  # Don't suppress exceptions


def get_current_task() -> Optional["Task"]:  # noqa: F821
    """
    Get the currently executing task from context.

    This can be called from anywhere within a task execution context
    to access the task instance without explicit parameter passing.

    Returns:
        Task instance if within task execution context, None otherwise

    Example:
        def some_deep_function():
            task = get_current_task()
            if task:
                print(f"Running in task {task.id}")
            else:
                print("Not in task context")
    """
    return _current_task.get()


def check_task_cancelled():
    """
    Check if the current task has been cancelled.

    This can be called from anywhere within a task execution context
    to gracefully handle cancellation. If called outside a task context,
    it does nothing (safe to use in code that may run outside tasks).

    The function will check the database for the current task's status
    and raise TaskCancelledException if the task has been cancelled.

    Raises:
        TaskCancelledException: If the current task is cancelled

    Example:
        def process_items(items):
            for item in items:
                check_task_cancelled()  # Check before each item
                process(item)

    Note:
        This is safe to call even if not in a task context - it will
        simply do nothing if no task is currently executing.
    """
    task = get_current_task()
    if task:
        task.check_cancelled()
