"""
Tests for task cancellation functionality.

This module tests the task cancellation infrastructure including:
- TaskCancelledException
- Task.check_cancelled() method
- Context manager (task_execution_context)
- check_task_cancelled() helper function
- Integration with Task._run()
"""

import threading
import time

import pytest

import tests.django_tests.testapp.models as models
from fullctl.django.models.concrete.tasks import TaskCancelledException
from fullctl.django.tasks.context import (
    check_task_cancelled,
    get_current_task,
    task_execution_context,
)


@pytest.mark.django_db
class TestTaskCancelledException:
    """Test the TaskCancelledException class"""

    def test_exception_creation(self):
        """Test that TaskCancelledException can be created with a task"""
        task = models.CancellableTask.create_task(10)
        exc = TaskCancelledException(task)

        assert isinstance(exc, IOError)
        assert exc.task == task
        assert str(task.id) in str(exc)

    def test_exception_attributes(self):
        """Test that exception has correct attributes"""
        task = models.CancellableTask.create_task(10)
        exc = TaskCancelledException(task)

        # Should have task attribute
        assert hasattr(exc, "task")
        assert exc.task.id == task.id


@pytest.mark.django_db
class TestTaskCheckCancelled:
    """Test the Task.check_cancelled() method"""

    def test_check_cancelled_raises_when_cancelled(self):
        """Test that check_cancelled() raises TaskCancelledException when task is cancelled"""
        task = models.CancellableTask.create_task(10)
        task.status = "running"
        task.save()

        # Cancel the task
        task.cancel("Test cancellation")

        # check_cancelled should raise
        with pytest.raises(TaskCancelledException) as exc_info:
            task.check_cancelled()

        assert exc_info.value.task.id == task.id

    def test_check_cancelled_does_not_raise_when_running(self):
        """Test that check_cancelled() doesn't raise when task is running"""
        task = models.CancellableTask.create_task(10)
        task.status = "running"
        task.save()

        # Should not raise
        try:
            task.check_cancelled()
        except TaskCancelledException:
            pytest.fail("check_cancelled() raised unexpectedly")

    def test_check_cancelled_does_not_raise_when_pending(self):
        """Test that check_cancelled() doesn't raise for pending tasks"""
        task = models.CancellableTask.create_task(10)
        # Task is pending by default

        # Should not raise
        try:
            task.check_cancelled()
        except TaskCancelledException:
            pytest.fail("check_cancelled() raised unexpectedly for pending task")

    def test_check_cancelled_refreshes_from_db(self):
        """Test that check_cancelled() gets fresh status from database"""
        task = models.CancellableTask.create_task(10)
        task.status = "running"
        task.save()

        # Get a fresh instance in another "context"
        task_ref = models.CancellableTask.objects.get(id=task.id)

        # Cancel using the reference
        task_ref.cancel("Cancelled from another context")

        # Original task should detect cancellation after check
        with pytest.raises(TaskCancelledException):
            task.check_cancelled()


@pytest.mark.django_db
class TestTaskExecutionContext:
    """Test the task_execution_context context manager"""

    def test_context_sets_current_task(self):
        """Test that entering context sets the current task"""
        task = models.CancellableTask.create_task(10)

        # Before entering context
        assert get_current_task() is None

        # Enter context
        with task_execution_context(task):
            # Inside context
            assert get_current_task() == task

        # After exiting context
        assert get_current_task() is None

    def test_context_returns_task(self):
        """Test that context manager returns the task"""
        task = models.CancellableTask.create_task(10)

        with task_execution_context(task) as ctx_task:
            assert ctx_task == task

    def test_context_cleanup_on_exception(self):
        """Test that context is cleaned up even when exception occurs"""
        task = models.CancellableTask.create_task(10)

        try:
            with task_execution_context(task):
                assert get_current_task() == task
                raise ValueError("Test exception")
        except ValueError:
            pass

        # Context should be cleaned up despite exception
        assert get_current_task() is None

    def test_nested_contexts(self):
        """Test that nested contexts work correctly"""
        task1 = models.CancellableTask.create_task(5)
        task2 = models.CancellableTask.create_task(10)

        with task_execution_context(task1):
            assert get_current_task() == task1

            # Enter nested context
            with task_execution_context(task2):
                assert get_current_task() == task2

            # Back to outer context
            assert get_current_task() == task1

        # All cleaned up
        assert get_current_task() is None


@pytest.mark.django_db
class TestCheckTaskCancelledHelper:
    """Test the check_task_cancelled() helper function"""

    def test_check_task_cancelled_with_no_context(self):
        """Test that check_task_cancelled() does nothing when no context"""
        # Should not raise when called outside task context
        try:
            check_task_cancelled()
        except Exception:
            pytest.fail("check_task_cancelled() should not raise outside context")

    def test_check_task_cancelled_in_context(self):
        """Test that check_task_cancelled() works inside context"""
        task = models.CancellableTask.create_task(10)
        task.status = "running"
        task.save()
        task.cancel("Test cancellation")

        with task_execution_context(task):
            # Should raise because task is cancelled
            with pytest.raises(TaskCancelledException):
                check_task_cancelled()

    def test_check_task_cancelled_from_deep_call_stack(self):
        """Test that check_task_cancelled() works from nested function calls"""

        def level_3():
            """Third level function"""
            check_task_cancelled()

        def level_2():
            """Second level function"""
            level_3()

        def level_1():
            """First level function"""
            level_2()

        task = models.CancellableTask.create_task(10)
        task.status = "running"
        task.save()
        task.cancel("Test cancellation")

        with task_execution_context(task):
            # Should raise from deep in call stack
            with pytest.raises(TaskCancelledException):
                level_1()


@pytest.mark.django_db(transaction=True)
class TestTaskRunCancellation:
    """Test cancellation integration with Task._run()"""

    def test_task_run_handles_cancellation_gracefully(self):
        """Test that _run() handles TaskCancelledException without marking as failed"""
        task = models.CancellableTask.create_task(iterations=100)

        # Start task in thread
        def run_task():
            task._run()

        thread = threading.Thread(target=run_task)
        thread.start()

        # Wait for task to actually start running
        max_wait = 2.0
        start = time.time()
        while time.time() - start < max_wait:
            task.refresh_from_db()
            if task.status == "running":
                break
            time.sleep(0.05)

        assert task.status == "running", f"Task never started running, status: {task.status}"

        # Cancel the task
        task.cancel("Test mid-execution cancel")

        # Wait for thread to finish
        thread.join(timeout=5)

        # Verify task is cancelled, not failed
        task.refresh_from_db()
        assert task.status == "cancelled"
        assert task.error is None
        assert "Test mid-execution cancel" in task.output

    def test_task_run_sets_execution_time_on_cancellation(self):
        """Test that execution time is recorded even when cancelled"""
        task = models.CancellableTask.create_task(iterations=100)

        def run_task():
            task._run()

        thread = threading.Thread(target=run_task)
        thread.start()

        # Wait for task to actually start running (not just pending)
        max_wait = 2.0
        start = time.time()
        while time.time() - start < max_wait:
            task.refresh_from_db()
            if task.status == "running":
                break
            time.sleep(0.05)

        assert task.status == "running", f"Task never started running, status: {task.status}"

        # Now cancel it
        task.cancel("Test cancel")
        thread.join(timeout=5)

        task.refresh_from_db()
        # Execution time should be recorded (> 0)
        # We just verify it's set, not a specific value due to timing variations
        assert task.time > 0

    def test_task_without_cancellation_checks_completes(self):
        """
        Test that task without checks completes even if cancelled.

        This demonstrates that tasks MUST explicitly check for cancellation.
        If a task never calls check_cancelled(), it will ignore cancellation
        requests and complete normally, overwriting the "cancelled" status.
        """
        task = models.NonCancellableTask.create_task(iterations=5)

        def run_task():
            task._run()

        thread = threading.Thread(target=run_task)
        thread.start()

        # Wait for task to start running
        max_wait = 2.0
        start = time.time()
        while time.time() - start < max_wait:
            task.refresh_from_db()
            if task.status == "running":
                break
            time.sleep(0.05)

        assert task.status == "running", f"Task never started running, status: {task.status}"

        # Cancel while running (but task won't notice because it doesn't check)
        task.cancel("This won't stop it")

        thread.join(timeout=2)

        # Task completes normally, overwriting "cancelled" with "completed"
        task.refresh_from_db()
        assert task.status == "completed"
        assert task.result == 5


@pytest.mark.django_db(transaction=True)
class TestCancellableTaskIntegration:
    """Integration tests for full cancellation workflow"""

    def test_cancellable_task_with_context_helper(self):
        """Test task using check_task_cancelled() from context"""
        task = models.CancellableTask.create_task(iterations=100)

        def run_task():
            task._run()

        thread = threading.Thread(target=run_task)
        thread.start()

        # Wait for task to start running
        max_wait = 2.0
        start = time.time()
        while time.time() - start < max_wait:
            task.refresh_from_db()
            if task.status == "running":
                break
            time.sleep(0.05)

        assert task.status == "running", f"Task never started running, status: {task.status}"

        task.cancel("Context helper test")
        thread.join(timeout=5)

        task.refresh_from_db()
        assert task.status == "cancelled"
        assert task.error is None

    def test_multiple_cancellation_checks(self):
        """Test that multiple cancellation checks work correctly"""
        task = models.CancellableTask.create_task(iterations=10)
        task.status = "running"
        task.save()

        # Cancel the task
        task.cancel("Multiple checks test")

        # Multiple checks should all raise
        for _ in range(3):
            with pytest.raises(TaskCancelledException):
                task.check_cancelled()

    def test_cancel_is_idempotent(self):
        """Test that calling cancel multiple times is safe"""
        task = models.CancellableTask.create_task(iterations=10)

        # Cancel multiple times
        task.cancel("First cancel")
        task.cancel("Second cancel")
        task.cancel("Third cancel")

        task.refresh_from_db()
        assert task.status == "cancelled"
        # Output should be from last cancel
        assert "Third cancel" in task.output

    def test_task_context_automatic_in_run(self):
        """Test that task context is automatically set by _run()"""
        task = models.CancellableTask.create_task(iterations=5)

        # Context should be None before execution
        assert get_current_task() is None

        # Create a flag to check if context was set during execution
        context_was_set = []

        # Monkey-patch the run method to capture context
        original_run = task.run

        def wrapped_run(*args, **kwargs):
            current = get_current_task()
            context_was_set.append(current)
            return original_run(*args, **kwargs)

        task.run = wrapped_run

        # Run the task
        task._run()

        # Verify context was set during execution
        assert len(context_was_set) > 0
        assert context_was_set[0] == task

        # Verify context is cleaned up after execution
        assert get_current_task() is None

    def test_cancellation_before_task_starts(self):
        """Test cancelling a task before it starts executing"""
        task = models.CancellableTask.create_task(iterations=10)

        # Cancel while still pending
        task.cancel("Cancelled before start")

        # Task should not start (status check in _run)
        task.refresh_from_db()
        assert task.status == "cancelled"

    def test_completed_task_check_cancelled_does_not_raise(self):
        """Test that checking cancellation on completed task doesn't raise"""
        task = models.CancellableTask.create_task(iterations=1)
        task._run()  # Let it complete

        task.refresh_from_db()
        assert task.status == "completed"

        # Checking cancellation on completed task should not raise
        try:
            task.check_cancelled()
        except TaskCancelledException:
            pytest.fail("check_cancelled() should not raise for completed task")


@pytest.mark.django_db(transaction=True)
class TestEdgeCases:
    """Test edge cases and error conditions"""

    def test_task_cancelled_multiple_times_in_execution(self):
        """Test task handles being cancelled multiple times during execution"""
        task = models.CancellableTask.create_task(iterations=100)

        def run_task():
            task._run()

        thread = threading.Thread(target=run_task)
        thread.start()

        # Wait for task to start running
        max_wait = 2.0
        start = time.time()
        while time.time() - start < max_wait:
            task.refresh_from_db()
            if task.status == "running":
                break
            time.sleep(0.05)

        assert task.status == "running", f"Task never started running, status: {task.status}"

        # Cancel multiple times
        task.cancel("First")
        task.cancel("Second")
        task.cancel("Third")

        thread.join(timeout=5)

        task.refresh_from_db()
        assert task.status == "cancelled"

    def test_check_cancelled_with_missing_task_id(self):
        """Test that check_cancelled raises error for unsaved tasks"""
        task = models.CancellableTask(op="task_cancellable")
        # Not saved - no ID yet

        # refresh_from_db() on unsaved object raises DoesNotExist or ValueError
        # depending on Django version, so we catch the broader exception
        with pytest.raises((ValueError, models.CancellableTask.DoesNotExist)):
            task.check_cancelled()
