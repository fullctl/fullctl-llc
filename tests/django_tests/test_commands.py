import pytest
from django.core import management


def test_fullctl_peeringdb_sync(db, dj_account_objects):
    with pytest.raises(SystemExit):
        management.call_command("fullctl_peeringdb_sync", "--help")


def test_fullctl_poll_tasks(db, dj_account_objects):
    with pytest.raises(SystemExit):
        management.call_command("fullctl_poll_tasks", "--help")


def test_fullctl_promote_user(db, dj_account_objects):
    with pytest.raises(SystemExit):
        management.call_command("fullctl_promote_user", "--help")


def test_fullctl_work_task(db, dj_account_objects):
    with pytest.raises(SystemExit):
        management.call_command("fullctl_work_task", "--help")
