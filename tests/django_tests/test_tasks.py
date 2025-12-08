import pytest
from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone
from unittest.mock import patch

import fullctl.django.tasks.orm as orm
import tests.django_tests.testapp.models as models
from fullctl.django.health_check import (
    health_check_task_heartbeat,
    health_check_task_stack_queue,
)
from fullctl.django.models.concrete.tasks import (
    TaskClaim,
    TaskClaimed,
    TaskHeartbeatError,
    TaskLimitError,
    TaskMaxAgeError,
    TaskSchedule,
    TaskScheduleClaim,
    TaskScheduleClaimed,
    TaskAlreadyStarted,
    Task,
)
from fullctl.django.tasks.util import worker_id


def backdate_task(task: Task, seconds: int) -> None:
    """
    Backdate a task's updated timestamp by a specified number of seconds.

    This is a test utility that temporarily disables the auto_now behavior
    on the updated field to allow manual backdating for testing cleanup
    and timeout scenarios.

    Args:
        task: The task instance to backdate
        seconds: Number of seconds to subtract from the current updated timestamp
    """
    try:
        task._meta.get_field("updated").auto_now = False
        task.updated = task.updated - timezone.timedelta(seconds=seconds)
        task.save()
    finally:
        task._meta.get_field("updated").auto_now = True

@pytest.mark.django_db
def test_task_with_max_run_time():
    task = models.TestTaskWithMaxRunTime.create_task(1, 2)

    orm.claim_task(task)

    task.created = task.created - timezone.timedelta(seconds=7200)
    task.updated = task.created
    try:
        # set updated auto_now to false
        task._meta.get_field("updated").auto_now = False
        task.save()
    finally:
        task._meta.get_field("updated").auto_now = True

    orm.tasks_max_time_reached()

    assert orm.fetch_tasks()


@pytest.mark.django_db
def test_fetch_tasks():
    assert orm.fetch_task() is None
    assert orm.fetch_tasks() == []

    task = models.TestTask.create_task(1, 2)
    assert task == orm.fetch_task()
    task2 = models.TestTask.create_task(1, 3)
    assert orm.fetch_tasks(limit=2) == [task, task2]


@pytest.mark.django_db
def test_claim_task():
    task = models.TestTask.create_task(1, 2)
    orm.claim_task(task)

    with pytest.raises(TaskClaimed) as execinfo:
        orm.claim_task(task)

    assert "Task already claimed by another worker:" in str(execinfo)


@pytest.mark.django_db
def test_work_tasks():
    task = models.TestTask.create_task(1, 2)

    orm.claim_task(task)

    assert task.queue_id
    assert task.taskclaim

    orm.work_task(task)

    assert task.status == "completed"
    assert int(task.output) == 3


@pytest.mark.django_db
def test_parent_task():
    task_par = models.TestTask.create_task(1, 2)
    task_chl = models.TestTask.create_task(7, 3, parent=task_par)

    # cant run child task before parent is finished

    with pytest.raises(IOError):
        orm.work_task(task_chl)

    tasks = orm.fetch_tasks()

    # child task should not be fetched while its waiting
    # for parent
    assert task_chl not in tasks
    assert task_par in tasks

    orm.work_task(task_par)

    tasks = orm.fetch_tasks()

    assert task_chl in tasks

    # child task can be worked now
    task_chl.refresh_from_db()
    orm.work_task(task_chl)


@pytest.mark.django_db
def test_task_qualifiers(settings):
    task = models.QualifierTestTask.create_task(1, 2)

    # worker qualifies, task should be in tasks

    settings.TEST_QUALIFIER = True
    assert task in orm.fetch_tasks()

    # worker no longer qualifiers, task should not be in tasks

    settings.TEST_QUALIFIER = False
    assert task not in orm.fetch_tasks()


@pytest.mark.django_db
def test_task_result():
    task = models.TestTask.create_task(1, 2)
    orm.work_task(task)
    assert task.result == 3


@pytest.mark.django_db
def test_task_limits():
    task = models.LimitedTask.create_task("test")
    with pytest.raises(TaskLimitError):
        task = models.LimitedTask.create_task("test")

    orm.work_task(task)
    task = models.LimitedTask.create_task("test")


@pytest.mark.django_db
def test_task_limits_with_id():
    task_a = models.LimitedTaskWithLimitId.create_task("test")
    task_b = models.LimitedTaskWithLimitId.create_task("other")
    with pytest.raises(TaskLimitError):
        task_a = models.LimitedTaskWithLimitId.create_task("test")
    with pytest.raises(TaskLimitError):
        task_b = models.LimitedTaskWithLimitId.create_task("other")

    orm.work_task(task_a)
    orm.work_task(task_b)
    task_a = models.LimitedTaskWithLimitId.create_task("test")
    task_b = models.LimitedTaskWithLimitId.create_task("other")


@pytest.mark.django_db
def test_task_limit_error_returns_message_without_limit_id_provided():
    models.LimitedTask.create_task("test")

    with pytest.raises(TaskLimitError) as exc_info:
        models.LimitedTask.create_task("test")

    assert "Task limit exceeded" == str(exc_info.value)


@pytest.mark.django_db
def test_task_limit_error_returns_message_with_limit_id_provided():
    task = models.LimitedTaskWithLimitId.create_task("test")

    with pytest.raises(TaskLimitError) as exc_info:
        raise TaskLimitError(task)

    assert "Task limit exceeded for task with limit id: test" == str(exc_info.value)


@pytest.mark.django_db
def test_schedule_limited_task_manually(dj_account_objects):
    org = dj_account_objects.org
    models.LimitedTaskWithLimitId.create_task("test")

    task_schedule = TaskSchedule.objects.create(
        org=org,
        task_config={
            "tasks": [
                {
                    "op": "task_limited_2",
                    "param": {"args": ["test"]},
                }
            ],
        },
        description="test",
        repeat=True,
        interval=3600,
        schedule=timezone.now(),
    )

    # This will not raise a TaskLimitError
    task_schedule.spawn_tasks()


@pytest.mark.django_db
def test_task_schedule_cannot_be_claimed_twice(dj_account_objects):
    """Test that a task schedule cannot be claimed twice."""
    org = dj_account_objects.org
    
    # Create a task schedule
    task_schedule = TaskSchedule.objects.create(
        org=org,
        task_config={
            # NO tasks so it is forced to raise a TaskScheduleClaimed and not a TaskAlreadyStarted
            "tasks": [
            ],
        },
        description="test claiming",
        repeat=True,
        interval=3600,
        schedule=timezone.now(),
    )

    schedule_date = task_schedule.schedule
    
    # First claim should succeed
    task_schedule.spawn_tasks()
    
    # reset the schedule date to the original
    task_schedule.schedule = schedule_date
    task_schedule.save()

    # Second claim should fail with TaskScheduleClaimed exception
    with pytest.raises(TaskScheduleClaimed) as exc_info:
        task_schedule.spawn_tasks()
    
    assert "Task schedule already claimed by another worker:" in str(exc_info.value)


@pytest.mark.django_db
def test_task_stack_queue_for_maximum_pending_tasks():
    settings.MAX_PENDING_TASKS = 10
    settings.TASK_MAX_AGE_THRESHOLD = 24

    for _ in range(11):
        models.TestTask.create_task(1, 2)

    with pytest.raises(TaskLimitError):
        health_check_task_stack_queue()


@pytest.mark.django_db
def test_task_stack_queue_for_tasks_exceeding_maximum_age_threshold():
    settings.MAX_PENDING_TASKS = 10
    settings.TASK_MAX_AGE_THRESHOLD = 1

    task = models.TestTask.create_task(1, 2)

    task.created = task.created - timezone.timedelta(hours=2)
    task.save()

    with pytest.raises(TaskMaxAgeError):
        health_check_task_stack_queue()


@pytest.mark.django_db
def test_task_heartbeat():
    task = models.TestTask.create_task(1, 2)
    task.status = "completed"
    task.save()
    task_heartbeat = models.TestTaskHeartbeat.objects.create(task=task)
    task_heartbeat.save()
    health_check_task_heartbeat()


@pytest.mark.django_db
def test_task_heartbeat_timeout():
    settings.HEALTH_CHECK_TASK_INTERVAL_SECONDS = 20
    task = models.TestTask.create_task(1, 2)
    task.status = "running"
    task.save()
    task_heartbeat = models.TestTaskHeartbeat.objects.create(task=task)
    task_heartbeat.timestamp = timezone.now() - timezone.timedelta(
        seconds=settings.HEALTH_CHECK_TASK_INTERVAL_SECONDS + 10
    )
    task_heartbeat.save()

    with pytest.raises(TaskHeartbeatError):
        health_check_task_heartbeat()


@pytest.mark.django_db
def test_cleanup_orphaned_running_tasks_with_stale_heartbeat():
    """Test that cleanup_orphaned_running_tasks marks tasks with stale heartbeats as failed."""
    task = models.TestTask.create_task(1, 2)
    task.status = "running"
    task.save()

    backdate_task(task, 60)
    
    # Create an old heartbeat (older than default timeout of 30 seconds)
    heartbeat = models.TestTaskHeartbeat.objects.create(task=task)
    old_timestamp = timezone.now() - timezone.timedelta(seconds=60)
    heartbeat.timestamp = old_timestamp
    heartbeat.save()
    
    assert task.status == "running"
    assert models.TestTaskHeartbeat.objects.filter(task=task).exists()
    
    orm.cleanup_orphaned_running_tasks()
    
    # Refresh and verify task is now failed
    task.refresh_from_db()
    assert task.status == "failed"
    assert "orphaned - no heartbeat detected for 30 seconds" in task.error
    assert str(old_timestamp) in task.error

    assert not models.TestTaskHeartbeat.objects.filter(task=task).exists()


@pytest.mark.django_db
def test_cleanup_orphaned_running_tasks_with_recent_heartbeat():
    """Test that cleanup_orphaned_running_tasks leaves tasks with recent heartbeats alone."""
    task = models.TestTask.create_task(1, 2)
    task.status = "running"
    task.save()
    
    # Create a recent heartbeat (within timeout)
    heartbeat = models.TestTaskHeartbeat.objects.create(task=task)
    recent_timestamp = timezone.now() - timezone.timedelta(seconds=15)
    heartbeat.timestamp = recent_timestamp
    heartbeat.save()
    
    assert task.status == "running"
    
    orm.cleanup_orphaned_running_tasks()
    
    # Refresh and verify task status unchanged
    task.refresh_from_db()
    assert task.status == "running"
    assert task.error is None or task.error == ""
    
    # Verify heartbeat still exists
    assert models.TestTaskHeartbeat.objects.filter(task=task).exists()


@pytest.mark.django_db
def test_cleanup_orphaned_running_tasks_with_custom_timeout(settings):
    """Test that cleanup_orphaned_running_tasks respects custom timeout settings."""
    settings.TASK_ORPHANED_HEARTBEAT_TIMEOUT = 60
    
    task = models.TestTask.create_task(1, 2)
    task.status = "running"
    task.save()

    backdate_task(task, 60)
    
    # Create a heartbeat that's 45 seconds old (within custom timeout)
    heartbeat = models.TestTaskHeartbeat.objects.create(task=task)
    old_timestamp = timezone.now() - timezone.timedelta(seconds=45)
    heartbeat.timestamp = old_timestamp
    heartbeat.save()
    
    # Run cleanup
    orm.cleanup_orphaned_running_tasks()
    
    # Task should still be running since it's within the 60-second timeout
    task.refresh_from_db()
    assert task.status == "running"
    
    # Now make the heartbeat older than the custom timeout
    heartbeat.timestamp = timezone.now() - timezone.timedelta(seconds=90)
    heartbeat.save()
    
    orm.cleanup_orphaned_running_tasks()
    
    # Now the task should be failed
    task.refresh_from_db()
    assert task.status == "failed"
    assert "orphaned - no heartbeat detected for 60 seconds" in task.error


@pytest.mark.django_db
def test_cleanup_orphaned_running_tasks_ignores_non_running_tasks():
    """Test that cleanup_orphaned_running_tasks only affects running tasks."""
    pending_task = models.TestTask.create_task(1, 2)
    pending_task.status = "pending"
    pending_task.save()
    
    completed_task = models.TestTask.create_task(3, 4)
    completed_task.status = "completed"
    completed_task.save()
    
    failed_task = models.TestTask.create_task(5, 6)
    failed_task.status = "failed"
    failed_task.save()
    
    # Create old heartbeats for all tasks
    old_timestamp = timezone.now() - timezone.timedelta(seconds=60)
    
    for task in [pending_task, completed_task, failed_task]:
        heartbeat = models.TestTaskHeartbeat.objects.create(task=task)
        heartbeat.timestamp = old_timestamp
        heartbeat.save()
    
    orm.cleanup_orphaned_running_tasks()
    
    # Verify none of the non-running tasks were affected
    for task in [pending_task, completed_task, failed_task]:
        task.refresh_from_db()
        assert task.status != "failed" or task.status == "failed"
        # Heartbeats should still exist for non-running tasks
        assert models.TestTaskHeartbeat.objects.filter(task=task).exists()


@pytest.mark.django_db
def test_cleanup_orphaned_running_tasks_with_no_heartbeat():
    """Test that old running tasks without heartbeats are marked as failed."""
    task = models.TestTask.create_task(1, 2)
    task.status = "running"
    task.save()

    # Backdate the task to make it older than the heartbeat timeout
    backdate_task(task, 60)

    assert not models.TestTaskHeartbeat.objects.filter(task=task).exists()

    # Run cleanup
    orm.cleanup_orphaned_running_tasks()

    # Task should now be marked as failed since it's old and has no heartbeat
    task.refresh_from_db()
    assert task.status == "failed"
    assert "orphaned - task still `running` but no heartbeat was ever received" in task.error


@pytest.mark.django_db
def test_cleanup_orphaned_running_tasks_ignores_recent_tasks():
    """Test that recently updated running tasks without heartbeats are not cleaned up."""
    task = models.TestTask.create_task(1, 2)
    task.status = "running"
    task.save()

    # Task is recent (not backdated), so it should not be cleaned up even without heartbeat
    assert not models.TestTaskHeartbeat.objects.filter(task=task).exists()

    # Run cleanup
    orm.cleanup_orphaned_running_tasks()

    # Task should remain running since it's recent
    task.refresh_from_db()
    assert task.status == "running"
    assert task.error is None or task.error == ""


@pytest.mark.django_db
def test_cleanup_orphaned_running_tasks_multiple_tasks():
    """Test cleanup with multiple tasks having different heartbeat states."""
    stale_task1 = models.TestTask.create_task(1, 2)
    stale_task1.status = "running"
    stale_task1.save()
    
    stale_task2 = models.TestTask.create_task(3, 4)
    stale_task2.status = "running"
    stale_task2.save()
    
    fresh_task = models.TestTask.create_task(5, 6)
    fresh_task.status = "running"
    fresh_task.save()
    
    # Create stale heartbeats for first two tasks
    old_timestamp = timezone.now() - timezone.timedelta(seconds=60)
    for task in [stale_task1, stale_task2]:
        heartbeat = models.TestTaskHeartbeat.objects.create(task=task)
        heartbeat.timestamp = old_timestamp
        heartbeat.save()
        backdate_task(task, 60)
    
    # Create recent heartbeat for third task
    recent_heartbeat = models.TestTaskHeartbeat.objects.create(task=fresh_task)
    recent_heartbeat.timestamp = timezone.now() - timezone.timedelta(seconds=10)
    recent_heartbeat.save()
    
    orm.cleanup_orphaned_running_tasks()
    
    stale_task1.refresh_from_db()
    stale_task2.refresh_from_db()
    fresh_task.refresh_from_db()
    
    # Stale tasks should be failed
    assert stale_task1.status == "failed"
    assert stale_task2.status == "failed"
    
    # Fresh task should still be running
    assert fresh_task.status == "running"
    
    assert not models.TestTaskHeartbeat.objects.filter(task=stale_task1).exists()
    assert not models.TestTaskHeartbeat.objects.filter(task=stale_task2).exists()
    assert models.TestTaskHeartbeat.objects.filter(task=fresh_task).exists()


@pytest.mark.django_db
def test_cleanup_orphaned_running_tasks_with_no_running_tasks():
    """Test that cleanup handles the case where there are no running tasks."""
    completed_task = models.TestTask.create_task(1, 2)
    completed_task.status = "completed"
    completed_task.save()
    
    old_heartbeat = models.TestTaskHeartbeat.objects.create(task=completed_task)
    old_heartbeat.timestamp = timezone.now() - timezone.timedelta(seconds=60)
    old_heartbeat.save()
    
    # Run cleanup - should complete without error
    orm.cleanup_orphaned_running_tasks()
    
    # Verify nothing was changed
    completed_task.refresh_from_db()
    assert completed_task.status == "completed"
    assert models.TestTaskHeartbeat.objects.filter(task=completed_task).exists()


@pytest.mark.django_db
def test_task_schedule_unique_claim_constraint(dj_account_objects):
    """Test that the TaskScheduleClaim enforces the unique constraint."""

    org = dj_account_objects.org

    # Create a task schedule
    task_schedule = TaskSchedule.objects.create(
        org=org,
        task_config={
            "tasks": [],
        },
        description="test claiming constraint",
        repeat=True,
        interval=3600,
        schedule=timezone.now(),
    )

    # Create first claim
    schedule_date = timezone.now()
    claim1 = TaskScheduleClaim.objects.create(
        task_schedule=task_schedule,
        worker_id=worker_id(),
        schedule_date=schedule_date,
    )
    assert claim1.id is not None

    # Use an atomic block to contain the IntegrityError
    try:
        with transaction.atomic():
            # Attempting to create a second claim with the same task_schedule and schedule_date
            # should raise an IntegrityError
            TaskScheduleClaim.objects.create(
                task_schedule=task_schedule,
                worker_id=worker_id(),
                schedule_date=schedule_date,
            )
            # If we get here, the test should fail
            assert False, "Expected IntegrityError was not raised"
    except IntegrityError:
        # This is expected, continue with the test
        pass

    # Creating a claim with a different schedule_date should succeed
    different_date = timezone.now() + timezone.timedelta(hours=1)
    claim2 = TaskScheduleClaim.objects.create(
        task_schedule=task_schedule,
        worker_id=worker_id(),
        schedule_date=different_date,
    )
    assert claim2.id is not None


@pytest.mark.django_db
def test_task_schedule_reschedules_even_when_task_creation_fails(dj_account_objects):
    """Test that task schedule gets rescheduled even if task creation fails."""

    org = dj_account_objects.org

    # Create a task schedule with invalid config that will cause task creation to fail
    initial_schedule = timezone.now()
    task_schedule = TaskSchedule.objects.create(
        org=org,
        task_config={
            "tasks": [
                {
                    "op": "nonexistent_task_type",  # This should cause create_tasks_from_json to fail
                    "param": {"args": ["test"]},
                }
            ],
        },
        description="test schedule resilience",
        repeat=True,
        interval=3600,
        schedule=initial_schedule,
    )

    original_schedule_time = task_schedule.schedule

    # Mock create_tasks_from_json to simulate failure
    with patch('fullctl.django.tasks.create_tasks_from_json') as mock_create_tasks:
        mock_create_tasks.side_effect = Exception("Task creation failed")

        # This should raise an exception but still reschedule
        with pytest.raises(Exception, match="Task creation failed"):
            task_schedule.spawn_tasks()

    # Refresh the object from database
    task_schedule.refresh_from_db()

    # Despite the task creation failure, the schedule should have been rescheduled
    assert task_schedule.schedule > original_schedule_time

    # Check that it was rescheduled approximately 3600 seconds later (allowing for small timing differences)
    expected_schedule = original_schedule_time + timezone.timedelta(seconds=3600)
    time_difference = abs((task_schedule.schedule - expected_schedule).total_seconds())
    assert time_difference < 1.0, f"Schedule difference too large: {time_difference} seconds"


@pytest.mark.django_db
def test_task_schedule_old_claims_cleanup(dj_account_objects):
    """Test that old TaskScheduleClaims get cleaned up after successful spawn."""

    org = dj_account_objects.org

    task_schedule = TaskSchedule.objects.create(
        org=org,
        task_config={
            "tasks": [],  # Empty so it doesn't fail
        },
        description="test claims cleanup",
        repeat=True,
        interval=3600,
        schedule=timezone.now(),
    )

    # Create some old claims for the same schedule
    old_claims = []
    for i in range(3):
        old_claim = TaskScheduleClaim.objects.create(
            task_schedule=task_schedule,
            worker_id=f"old_worker_{i}",
            schedule_date=task_schedule.schedule - timezone.timedelta(hours=i+1),
        )
        old_claims.append(old_claim)

    # Verify old claims exist
    assert TaskScheduleClaim.objects.filter(task_schedule=task_schedule).count() == 3

    # Spawn tasks should clean up old claims and create a new one
    task_schedule.spawn_tasks()

    # Should now have only one claim (the new one)
    remaining_claims = TaskScheduleClaim.objects.filter(task_schedule=task_schedule)
    assert remaining_claims.count() == 1

    # The remaining claim should be for the current worker
    new_claim = remaining_claims.first()
    assert new_claim.worker_id == worker_id()

    # All old claims should be gone
    for old_claim in old_claims:
        assert not TaskScheduleClaim.objects.filter(id=old_claim.id).exists()