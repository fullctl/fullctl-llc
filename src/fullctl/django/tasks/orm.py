"""
ORM based task delegation
"""

import time
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from fullctl.django.models import (
    Task,
    TaskAlreadyStarted,
    TaskClaimed,
    TaskSchedule,
    WorkerUnqualified,
)
from fullctl.django.models.concrete.tasks import TaskClaim, TaskLimitError
from fullctl.django.tasks import requeue as requeue_task
from fullctl.django.tasks import specify_task
from fullctl.django.tasks.util import worker_id

# (Task, timestamp)
# tasks that are in the recheck stack are not
# to be worked on until the timestamp has passed
# this is to avoid excess re-checking of qualifiers
RECHECK_STACK = []

# the longer a task has been in the recheck stack
# the longer the recheck time will be, up until a max
# time specified in the TASK_RECHECK_DECAY_MAX setting
RECHECK_DECAY = {}


def clean_recheck_stack(now: float):
    """
    Cleans the recheck stack of tasks that need to be rechecked
    """

    global RECHECK_STACK

    RECHECK_STACK = [(task, ts) for task, ts in RECHECK_STACK if ts > now]


def fetch_task(**filters):
    """
    Checks for the next available and qualifying
    tasks and returns it
    """

    tasks = fetch_tasks(limit=1, **filters)
    if tasks:
        return tasks[0]
    return None


def set_task_as_failed(generic_task, error_message=None, requeue=False):
    """
    Set task to failed with error information and re-queue
    """

    generic_task.status = "failed"
    generic_task.error = error_message
    generic_task.save()
    if requeue:
        requeue_task(generic_task)


def tasks_max_time_reached():
    """
    Requeues tasks that have reached their max run time
    """
    running_tasks = Task.objects.filter(
        status__in=["running", "pending"], queue_id__isnull=False
    )

    if not running_tasks.exists():
        return

    for generic_task in running_tasks:
        task = specify_task(generic_task)
        if not task.max_run_time:
            continue

        time_delta = timedelta(seconds=task.max_run_time)
        if (task.created + time_delta) < timezone.now():
            task.cancel("max run time reached")
            requeue_task(task)


def fetch_tasks(limit=1, **filters):
    """
    fetches pending tasks ready to be worked on
    """

    tasks = []
    now = time.time()

    DECAY_MAX = getattr(settings, "TASK_RECHECK_DECAY_MAX", 3600)

    # filter tasks waiting for execution
    qset = Task.objects.filter(status="pending", queue_id__isnull=True)

    if filters:
        qset = qset.filter(**filters)

    clean_recheck_stack(now)

    # exclude tasks that are in the recheck stack
    qset = qset.exclude(id__in=[task.id for task, _ in RECHECK_STACK])

    # order_history by date of -requeued and date of creation
    # requeued tasks are higher priority since they were meant
    # to be worked on earlier
    qset = qset.order_by("-requeued", "created")

    skip_tasks = {}

    # no pending tasks for this task model
    if not qset.exists():
        return tasks

    # limit to scanning 25 oldest tasks at a time, may need to adust
    # but we definitely dont want it to scan all pending tasks if there
    # is 1000s of them
    for task in qset[:25]:
        if task.op in skip_tasks:
            # task worker has been blocked from working on this
            # task op based on certain task properties

            skip = False

            for qualifier, ids in skip_tasks[task.op].items():
                # we check if the qualifier that blocked the worker
                # earlier in the loop matches the current task
                # if it does, we skip the task

                if qualifier.ids(task) == ids:
                    skip = True
                    break

            if skip:
                continue

        if task.parent_id and task.parent.status != "completed":
            if task.parent.status in ["failed", "cancelled"]:
                task.cancel(f"parent status: {task.parent.status}")
            continue
        try:
            task = specify_task(task)
            task.qualifies
            tasks.append(task)

            if task.id in RECHECK_DECAY:
                del RECHECK_DECAY[task.id]

        except WorkerUnqualified as exc:
            # worker temporary or permanently unqualified for this task type
            # block it from fetching more tasks of this type for this
            # poll cycle.
            #
            # this is to prevent it from accidentally starting
            # a more recent task because the blocking task gets solved
            # before the loop is complete) - race condition?

            if task.op not in skip_tasks:
                skip_tasks[task.op] = {}

            skip_tasks[task.op][exc.qualifier] = exc.qualifier.ids(task)

            # if the qualifier has a recheck time, add it to the recheck stack
            if exc.qualifier.recheck_time:
                if task.id in RECHECK_DECAY:
                    RECHECK_DECAY[task.id] += 1
                else:
                    RECHECK_DECAY[task.id] = 1

                recheck_time = min(
                    exc.qualifier.recheck_time * RECHECK_DECAY[task.id], DECAY_MAX
                )
                RECHECK_STACK.append((task, now + recheck_time))

            continue

        if len(tasks) == limit:
            return tasks

    return tasks


@transaction.atomic
def claim_task(task):
    """
    Claims the specified task
    """

    try:
        claim = TaskClaim.objects.create(task=task, worker_id=worker_id())
        task.queue_id = claim.worker_id
        task.save()
        return claim
    except IntegrityError as exc:
        print(exc)
        raise TaskClaimed(task)


def work_task(task):
    """
    processes the specified task
    """
    task._run()


def progress_schedules(**filters):
    """
    fetch and process due task schedules (one at a time)
    """

    schedule = (
        TaskSchedule.objects.filter(schedule__lte=timezone.now(), status="ok")
        .order_by("schedule")
        .first()
    )
    if not schedule:
        return

    try:
        schedule.spawn_tasks()
    except (TaskAlreadyStarted, TaskLimitError):
        schedule.reschedule()
