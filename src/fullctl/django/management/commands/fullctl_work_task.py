import time
import traceback

import psycopg
import structlog

from fullctl.django.management.commands.base import CommandInterface
from fullctl.django.models import Task
from fullctl.django.tasks.orm import set_task_as_failed, specify_task, work_task

log = structlog.get_logger("django")


class Command(CommandInterface):
    help = "Process the specified task"

    always_commit = True

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument("task_id", nargs="?")

    def handle(self, *args, **kwargs):
        self.task_id = kwargs.get("task_id")
        try:
            super().handle(*args, **kwargs)

            task = Task.objects.get(id=self.task_id)
            if getattr(self, "error", None) and not task.error:
                # failure, but wasn't within the context
                # of the task execution logic, transfer error
                # to task
                set_task_as_failed(task, self.error)

            if task.error:
                self.log_info("Task failed")
                self.log_error(task.error)
            else:
                self.log_info("Task finished")

        except Exception as exc:
            log.exception("Error in task run", exc=exc)
            self.handle_outer_error(exc)

    def run(self, *args, **kwargs):
        task_id = kwargs.get("task_id")
        task = specify_task(Task.objects.get(id=task_id))
        self.log_info(f"Processing {task}")
        work_task(task)

    def handle_outer_error(self, exc: Exception, retries: int = 5):

        """
        Handles errors that happen when setting up the task for processing

        This catches issues such as temporary database failures.
        """

        try:
            if isinstance(exc, psycopg.OperationalError):
                # db issue, give time to recover
                time.sleep(3)
            task = specify_task(Task.objects.get(id=self.task_id))
            # set task as failed
            set_task_as_failed(task, traceback.format_exc())
        except Exception as exc:
            log.exception(
                f"Error in task run (error cleanup, retries={retries})", exc=exc
            )
            if retries > 0:
                self.handle_outer_error(exc, retries - 1)
                # if error is never recovered during retries
                # task will end up orphaned as `pending` and will be eventually
                # re-queued by the poller whenever the max age limit is hit.
