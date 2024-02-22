"""
Defines an extendible healthcheck process for FullCtl services.
"""
from django.conf import settings
from django.db import connection
from django.utils import timezone

from fullctl.django.models.concrete.tasks import Task, TaskLimitError, TaskMaxAgeError

__all__ = [
    "register",
    "check_all",
    "HEALTH_CHECKS",
]

# holds all registered health checks
HEALTH_CHECKS = {}


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


def check_all() -> dict:
    """
    Run all registered health checks.
    """
    results = {}
    for name, func in HEALTH_CHECKS.items():
        results[name] = func()

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
