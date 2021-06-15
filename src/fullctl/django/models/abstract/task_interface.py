import datetime
import json
import subprocess
import traceback

import pytz
from django.core.exceptions import ValidationError
from django.db import models

from fullctl.django.models.abstract.base import HandleRefModel
from fullctl.django.tasks import launch_task


class TaskLimitError(IOError):
    pass


class Task(HandleRefModel):

    """
    Describes an asynchronous task

    Task status values:
        - pending: task waiting for execution
        - running: task is currently executing
        - completed: task completed succesfully
        - failed: task ended due to error
    """

    op = models.CharField(max_length=255)

    param_json = models.TextField(
        blank=True, null=True, help_text="json containing args and kwargs"
    )
    error = models.TextField(
        blank=True,
        null=True,
        help_text="if the task failed will contain " "traceback or error info",
    )
    output = models.TextField(
        blank=True,
        null=True,
        help_text="task output - can also be used to " "store results",
    )

    queue_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        help_text="task queue id (celery task id)",
    )

    limit = -1

    class Meta:
        abstract = True

    class HandleRef:
        tag = "task"

    @property
    def param(self):
        """
        Will return a dict from the param_json value
        """
        if self.param_json:
            return json.loads(self.param_json)
        return {"args": [], "kwargs": {}}

    @param.setter
    def param(self, param):
        """
        Will take a dict and convert to json and
        store in the param_json field
        """
        self.param_json = json.dumps(param)

    def clean(self):
        super().clean()
        op_name = f"op_{self.op}"
        if not hasattr(self, op_name):
            raise ValidationError(f"The operation `{op_name}` does not exist")

        if not callable(getattr(self, op_name)):
            raise ValidationError(f"The operation `{op_name}` is not callable")

        try:
            if self.param_json:
                json.loads(self.param_json)
        except Exception as exc:
            raise ValidationError(f"Parameters could not be JSON encoded: {exc}")

    def _complete(self, output):
        self.output = output
        self.status = "completed"
        self.save()

    def _fail(self, error):
        self.error = error
        self.status = "failed"
        self.save()

    def _run(self):
        self.status = "running"
        self.save()
        try:
            op = getattr(self, f"op_{self.op}")
            param = self.param
            output = op(*param["args"], **param["kwargs"])
            self._complete(output)
        except Exception:
            self._fail(traceback.format_exc())

    def run_command(self, command):
        p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        output, error = p.communic


class TaskContainer(HandleRefModel):

    """
    Decribes a model that is able to spawn tasks

    Needs to implement a `task_class` property
    that returns the model to use for task storage
    """

    class Meta:
        abstract = True

    @property
    def task_class(self):
        """override this"""
        return Task

    @property
    def tasks_active(self):
        return self.task_set.exclude(status__in=["completed", "failed"])

    def task_validate(self, task):
        if task.limit > -1:
            if self.tasks_active.filter(op=task.op) > task.limit:
                raise TaskLimitError(task.op)
        task.full_clean()
        return task

    def start_task(self, op, *args, **kwargs):
        task = self.task_class(
            status="pending",
            op=op,
            owner=self,
        )
        task.param = {"args": args, "kwargs": kwargs}
        task = self.task_validate(task)
        task.save()
        launch_task(task)
        return task

    def task_time(self, op=None):
        """
        Returns the amount of time (in seconds) that has passed
        since a task has been run.

        Keyword Argument(s):
            - op(str): if specified only consider tasks with that op

        Returns:
            - None: if no task has been run
            - int: seconds since task has been run
        """
        qs = self.task_set.all().order_by("-created")
        if op:
            qs.filter(op=op)

        task = qs.first()

        if not task:
            return None

        return (
            datetime.datetime.now().replace(tzinfo=pytz.UTC) - task.updated
        ).total_seconds()
