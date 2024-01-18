"""
ORM based task delegation
"""

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
from fullctl.django.tasks import specify_task
from fullctl.django.tasks.util import worker_id


def fetch_task(**filters):
    """
    Checks for the next available and qualifying
    tasks and returns it
    """

    tasks = fetch_tasks(limit=1, **filters)
    if tasks:
        return tasks[0]
    return None


def fetch_tasks(limit=1, **filters):
    """
    fetches pending tasks ready to be worked on
    """

    tasks = []

    # filter tasks waiting for execution
    qset = Task.objects.filter(status="pending", queue_id__isnull=True)

    if filters:
        qset = qset.filter(**filters)

    # order_history by date of creation
    qset = qset.order_by("created")

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
