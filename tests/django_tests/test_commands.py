# import magicmock
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core import management

import tests.django_tests.testapp.models as models
from fullctl.django.models import Task
from fullctl.django.tasks.orm import specify_task


def test_fullctl_poll_tasks(db, dj_account_objects):
    with pytest.raises(SystemExit):
        management.call_command("fullctl_poll_tasks", "--help")

def test_unresolved_task(db, dj_account_objects):
    task = models.UnregisteredTestTask.create_task()

    with pytest.raises(KeyError):
        task = specify_task(task)


def test_fullctl_promote_user(db, dj_account_objects_c):
    management.call_command("fullctl_promote_user", "user_test_c", "--commit")
    User = get_user_model()
    user = User.objects.get(username="user_test_c")

    assert user.is_superuser is True
    assert user.is_staff is True


def test_fullctl_work_task(db, dj_account_objects):
    task = models.TestTask.create_task(1, 2)
    management.call_command("fullctl_work_task", "1")
    task = specify_task(Task.objects.get(id=1))

    assert task.status == "completed"
    assert int(task.output) == 3


@patch("fullctl.django.management.commands.fullctl_work_task.Command.run")
def test_fullctl_work_task_error_handling_in_run(mock_run, db, dj_account_objects):
    # test error handling of errors in `run` call
    task = models.TestTask.create_task(1, 2)
    mock_run.side_effect = Exception("Test exception")

    management.call_command("fullctl_work_task", "1")
    task = specify_task(Task.objects.get(id=1))

    assert task.status == "failed"
    assert "Test exception" in task.error


@patch("fullctl.django.management.commands.base.CommandInterface.handle")
def test_fullctl_work_task_error_handling_in_handle(
    mock_handle, db, dj_account_objects
):
    # test error handling of errors in `handle` call
    task = models.TestTask.create_task(1, 2)
    mock_handle.side_effect = Exception("Test exception")

    management.call_command("fullctl_work_task", "1")
    task = specify_task(Task.objects.get(id=1))

    assert task.status == "failed"
    assert "Test exception" in task.error


def test_fullctl_work_task_fail(db, dj_account_objects):
    task = models.FailingTask.create_task()
    management.call_command("fullctl_work_task", "1")
    task = specify_task(Task.objects.get(id=1))

    assert task.status == "failed"


def test_fullctl_prune_completed_tasks(db, dj_account_objects):
    task = models.TestTask.create_task(1, 2)
    task.status = "completed"
    task.save()

    management.call_command("fullctl_manage_tasks", "prune", commit=True, age=0)

    assert Task.objects.count() == 0
    assert Task.objects.filter(id=task.id).count() == 0


def test_fullctl_prune_failed_tasks(db, dj_account_objects):
    task = models.TestTask.create_task(1, 2)
    task.status = "failed"
    task.save()

    management.call_command("fullctl_manage_tasks", "prune", commit=True, age=0)

    assert Task.objects.count() == 0
    assert Task.objects.filter(id=task.id).count() == 0


def test_fullctl_prune_cancelled_tasks(db, dj_account_objects):
    task = models.TestTask.create_task(1, 2)
    task.status = "cancelled"
    task.save()

    management.call_command("fullctl_manage_tasks", "prune", commit=True, age=0)

    assert Task.objects.count() == 0
    assert Task.objects.filter(id=task.id).count() == 0


def test_fullctl_doesnt_prune_pending_tasks(db, dj_account_objects):
    task = models.TestTask.create_task(1, 2)

    management.call_command("fullctl_manage_tasks", "prune", commit=True, age=0)

    assert Task.objects.count() == 1
    assert Task.objects.filter(id=task.id).count() == 1


def test_fullctl_doesnt_prune_running_tasks(db, dj_account_objects):
    task = models.TestTask.create_task(1, 2)
    task.status = "running"
    task.save()

    management.call_command("fullctl_manage_tasks", "prune", commit=True, age=0)

    assert Task.objects.count() == 1
    assert Task.objects.filter(id=task.id).count() == 1


def test_fullctl_doesnt_prune_young_tasks(db, dj_account_objects):
    task = models.TestTask.create_task(1, 2)
    task.status = "completed"
    task.save()

    management.call_command("fullctl_manage_tasks", "prune", commit=True, age=5)

    assert Task.objects.count() == 1
    assert Task.objects.filter(id=task.id).count() == 1
