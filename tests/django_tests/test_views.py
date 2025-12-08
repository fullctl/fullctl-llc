from unittest.mock import patch

from django.conf import settings
from django.test.client import Client
from django.utils import timezone

import tests.django_tests.testapp.models as models


def test_health_check(db):
    """
    Use django test client to request `/health` and check if the response
    is ok
    """
    settings.MAX_PENDING_TASKS = 10
    settings.TASK_MAX_AGE_THRESHOLD = 24

    client = Client()
    response = client.get("/health/")
    assert response.status_code == 200
    assert b'"task_stack_queue": {"ok": true}' in response.content
    assert b'"db": {"ok": true}' in response.content


def test_failing_health_check(db):
    """
    Use django test client to request `/health` and check if the response
    is ok
    """

    settings.MAX_PENDING_TASKS = 10
    settings.TASK_MAX_AGE_THRESHOLD = 24

    client = Client()

    # mock a sideeffect for django.db.connection.cursor
    with patch("django.db.connection.cursor") as mock_cursor:
        mock_cursor.side_effect = Exception("Test exception")
        response = client.get("/health/")
        assert response.status_code == 200
        assert b'"db": {"ok": false' in response.content


def test_health_check_task_stack_queue(db):
    """
    Use django test client to request `/health` and check if the response
    is ok
    """

    settings.MAX_PENDING_TASKS = 10
    settings.TASK_MAX_AGE_THRESHOLD = 24

    for _ in range(10):
        models.TestTask.create_task(1, 2)

    client = Client()

    response = client.get("/health/")
    assert response.status_code == 200
    assert b'"task_stack_queue": {"ok": true}' in response.content
    assert b'"db": {"ok": true}' in response.content


def test_failing_health_check_task_stack_queue_maximum_pending_tasks(db):
    """
    Test the health check for the task stack queue for tasks that exceed the
    maximum pending tasks
    """

    settings.MAX_PENDING_TASKS = 10
    settings.TASK_MAX_AGE_THRESHOLD = 24

    for _ in range(11):
        models.TestTask.create_task(1, 2)

    client = Client()

    response = client.get("/health/")
    assert response.status_code == 200
    assert b'"task_stack_queue": {"ok": false' in response.content


def test_failing_health_check_task_stack_queue_for_maximum_age_threshold(db):
    """
    Test the health check for the task stack queue for tasks that exceed the
    maximum age threshold
    """

    settings.MAX_PENDING_TASKS = 10
    settings.TASK_MAX_AGE_THRESHOLD = 1

    task = models.TestTask.create_task(1, 2)

    task.created = task.created - timezone.timedelta(hours=2)
    task.save()

    client = Client()

    response = client.get("/health/")
    assert response.status_code == 200
    assert b'"task_stack_queue": {"ok": false' in response.content
