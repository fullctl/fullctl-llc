import pytest
from django.core.management import call_command

import tests.django_tests.testapp.models as models
from fullctl.django.management.commands.fullctl_poll_tasks import Command, Worker
from fullctl.django.management.commands.fullctl_work_task import (
    Command as WorkTaskCommand,
)
from fullctl.django.models import TaskHeartbeat
from fullctl.django.models.concrete.tasks import TaskLimitError


@pytest.mark.django_db
class TestWorkerNoMock:
    def test_worker_initialization(self):
        """Test worker initialization with different parameters"""
        # Default worker
        worker = Worker()
        assert worker.id is not None
        assert worker.task is None
        assert worker.process is None
        assert worker.self_selecting is False
        assert worker.poll_interval == 3.0
        assert worker.max_tasks == 0

        # Self-selecting worker with custom parameters
        worker = Worker(self_selecting=True, poll_interval=5.0, max_tasks=10)
        assert worker.self_selecting is True
        assert worker.poll_interval == 5.0
        assert worker.max_tasks == 10

    def test_worker_set_task(self):
        """Test setting task on worker"""
        worker = Worker()
        task = models.TestTask.create_task(1, 2)
        worker.set_task(task)
        assert worker.task == task

        # Setting a task when one is already assigned should raise an error
        with pytest.raises(OSError):
            worker.set_task(models.TestTask.create_task(3, 4))


@pytest.mark.django_db
class TestPollTasksCommand:
    def test_worker_available_property(self):
        """Test the worker_available property"""
        cmd = Command()

        # No workers - should return False
        cmd.workers = []
        assert not cmd.worker_available

        # All workers busy
        worker1 = Worker()
        worker1.set_task(models.TestTask.create_task(1, 2))
        worker2 = Worker()
        worker2.set_task(models.TestTask.create_task(3, 4))
        cmd.workers = [worker1, worker2]
        assert not cmd.worker_available

        # One worker available
        worker3 = Worker()  # No task assigned
        cmd.workers = [worker1, worker2, worker3]
        assert cmd.worker_available


@pytest.mark.django_db
class TestWorkTaskCommand:
    def test_task_execution_direct(self):
        """Test direct execution of a task through the command"""
        # Create a task
        task = models.TestTask.create_task(1, 2)

        # Execute the task with the command
        call_command("fullctl_work_task", str(task.id))

        # Verify the task was completed
        task.refresh_from_db()
        assert task.status == "completed"
        assert int(task.output) == 3

    def test_task_execution_error(self):
        """Test task execution with error"""
        # Create a task that will fail
        task = models.FailingTask.create_task()

        # Execute the task with the command
        call_command("fullctl_work_task", str(task.id))

        # Verify the task has error status
        task.refresh_from_db()
        assert task.status == "failed"
        assert "invalid literal for int()" in task.error

    def test_task_limit_behavior(self):
        """Test the task limit behavior"""
        # Create a task that has a limit of 1
        task1 = models.LimitedTask.create_task("test")

        # Try to create another task - should raise error
        with pytest.raises(TaskLimitError):
            models.LimitedTask.create_task("test")

        # Execute the first task
        call_command("fullctl_work_task", str(task1.id))

        # Now we should be able to create another task
        task2 = models.LimitedTask.create_task("test")
        assert task2 is not None

    def test_work_task_command_once_flag(self):
        """Test WorkTaskCommand with once flag behaves correctly"""
        # Without mocking, we need to test the command behavior directly
        WorkTaskCommand()

        # Create two tasks
        task1 = models.TestTask.create_task(1, 2)
        task2 = models.TestTask.create_task(3, 4)

        # Use call_command instead of direct handle() call
        call_command("fullctl_work_task", "--once", "--poll-interval=0.1")

        # One task should be completed, the other should be pending
        task1.refresh_from_db()
        task2.refresh_from_db()

        # At least one of the tasks should be completed
        assert (task1.status == "completed" and task2.status == "pending") or (
            task1.status == "pending" and task2.status == "completed"
        )

    def test_work_task_command_max_tasks(self):
        """Test WorkTaskCommand with max_tasks limit behaves correctly"""
        # Create multiple tasks
        tasks = [
            models.TestTask.create_task(i, i + 1) for i in range(5)  # Create 5 tasks
        ]

        # Use call_command instead of direct handle() call
        call_command("fullctl_work_task", "--max-tasks=2", "--poll-interval=0.1")

        # Refresh tasks from db
        for task in tasks:
            task.refresh_from_db()

        # Count completed tasks
        completed = sum(1 for task in tasks if task.status == "completed")

        # Exactly 2 tasks should be completed
        assert (
            completed == 2
        ), f"Expected 2 tasks to be completed, but {completed} were completed"

    @pytest.mark.skip(
        "Skipping task heartbeat as thread would run into - DatabaseError: Connection already closed - error"
    )
    def test_task_heartbeat_tracking(self):
        """Test task heartbeat tracking"""
        task = models.TestTask.create_task(1, 2)
        assert not TaskHeartbeat.objects.filter(task=task).exists()
        cmd = WorkTaskCommand()
        cmd.handle(task_id=str(task.id), poll_interval=3.0)
        task.refresh_from_db()
        assert task.status == "completed"
        task_heartbeat = TaskHeartbeat.objects.get(task=task)
        assert task_heartbeat.timestamp
