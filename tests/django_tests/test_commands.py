import pytest
from django.contrib.auth import get_user_model
from django.core import management

import tests.django_tests.testapp.models as models
from fullctl.django.models import Task
from fullctl.django.tasks.orm import specify_task


def test_fullctl_peeringdb_sync(db, dj_account_objects):
    with pytest.raises(SystemExit):
        management.call_command("fullctl_peeringdb_sync", "--help")


def test_fullctl_poll_tasks(db, dj_account_objects):
    with pytest.raises(SystemExit):
        management.call_command("fullctl_poll_tasks", "--help")


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


def test_fullctl_work_task_fail(db, dj_account_objects):
    task = models.FailingTask.create_task()
    management.call_command("fullctl_work_task", "1")
    task = specify_task(Task.objects.get(id=1))

    assert task.status == "failed"
