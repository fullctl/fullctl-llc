"""
Defines an extendible healthcheck process for FullCtl services.
"""

from django.conf import settings
from django.db import connection
from django.utils import timezone

from fullctl.django.models.concrete.tasks import (
    Task,
    TaskHeartbeat,
    TaskHeartbeatError,
    TaskLimitError,
    TaskMaxAgeError,
)

__all__ = [
    "register",
    "check_all",
    "HEALTH_CHECKS",
]

# holds all registered health checks
HEALTH_CHECKS = {}

HEALTH_CHECK_TASK_INTERVAL_SECONDS = getattr(
    settings, "HEALTH_CHECK_TASK_INTERVAL_SECONDS", 20
)


class register:
    """
    Registers a health check function.

    The function will be called with no arguments.

    It should raise an exception if the check fails.
    """

    def __init__(self, name):
        self.name = name

    def __call__(self, func):
        HEALTH_CHECKS[self.name] = func
        return func


def check_all(exclude: list[str] = None) -> dict:
    """
    Run all registered health checks.
    """
    results = {}
    for name, func in HEALTH_CHECKS.items():
        if exclude and name in exclude:
            results[name] = {"excluded": True, "ok": True}
            continue
        try:
            func()
            results[name] = {"ok": True}
        except Exception as exc:
            results[name] = {"ok": False, "error": str(exc)}

    return results


@register("task_stack_queue")
def health_check_task_stack_queue():
    """
    Tests the task stack queue
    """
    pending_tasks = Task.objects.filter(status="pending", queue_id__isnull=True)

    if pending_tasks.exists():
        # check if the number of pending tasks exceeds the max limit
        if pending_tasks.count() > settings.MAX_PENDING_TASKS:
            raise TaskLimitError()

        # check if the age of the oldest pending task exceeds the limit
        threshold_hours = settings.TASK_MAX_AGE_THRESHOLD
        threshold_datetime = timezone.now() - timezone.timedelta(hours=threshold_hours)

        old_pending_tasks = pending_tasks.filter(
            created__lt=threshold_datetime
        ).exists()
        if old_pending_tasks:
            raise TaskMaxAgeError()


@register("task_heartbeat")
def health_check_task_heartbeat():
    """
    Tests the task heartbeat
    """
    running_tasks = Task.objects.filter(status__in=["pending", "running"])
    long_running_task_heartbeats = TaskHeartbeat.objects.filter(
        timestamp__lte=timezone.now()
        - timezone.timedelta(seconds=HEALTH_CHECK_TASK_INTERVAL_SECONDS),
        task__in=running_tasks,
    )
    if long_running_task_heartbeats.exists():
        raise TaskHeartbeatError(
            f"Long running tasks: {[str(task) for task in long_running_task_heartbeats]}"
        )


@register("db")
def health_check_db():
    """
    Performs a simple database version query
    """
    # postgresql
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute("SELECT version()")
    # sqlite
    elif connection.vendor == "sqlite":
        with connection.cursor() as cursor:
            cursor.execute("SELECT sqlite_version()")
    # fallback to default (postgresql, in case vendor naming changes in the future)
    else:
        with connection.cursor() as cursor:
            cursor.execute("SELECT version()")
