import asyncio
import datetime
import json
import subprocess
import time
import traceback
from io import StringIO

from asgiref.sync import sync_to_async
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

import fullctl.django.tasks
from fullctl.django.models.abstract.base import HandleRefModel
from fullctl.django.tasks.qualifiers import Dynamic
from fullctl.django.tasks.util import worker_id

__all__ = [
    "LimitAction",
    "TaskClaimed",
    "WorkerUnqualified",
    "TaskLimitError",
    "TaskAlreadyStarted",
    "ParentTaskNotFinished",
    "Task",
    "TaskClaim",
    "TaskSchedule",
    "CallCommand",
]


class LimitAction:
    error = 0
    silent = 1


class TaskClaimed(IOError):
    def __init__(self, task):
        super().__init__(f"Task already claimed by another worker: {task}")


class WorkerUnqualified(IOError):
    def __init__(self, task, qualifier):
        super().__init__(
            f"Worker does not qualify to process this task: {task}, {qualifier}"
        )
        self.qualifier = qualifier


class TaskLimitError(IOError):
    """
    Raised when there are currently too many pending
    instances of a task
    """

    def __init__(self, task=None):
        if task is None:
            message = "Task limit exceeded"
        else:
            message = (
                f"Task limit exceeded for task with limit id: {task.generate_limit_id}"
            )

        super().__init__(message)


class TaskAlreadyStarted(IOError):
    """
    Raised when trying to work a task that is already
    started
    """

    pass


class TaskMaxAgeError(IOError):
    """
    Raised when a pending task is older than the
    specified threshold
    """

    pass


class ParentTaskNotFinished(IOError):
    """
    Raised when trying to work a child task
    before the parent task has finished
    """

    pass


class Task(HandleRefModel):

    """
    Describes an asynchronous task

    Task status values:
        - pending: task waiting for execution
        - running: task is currently executing
        - completed: task completed succesfully
        - failed: task ended due to error
        - cancelled: task canceled
    """

    op = models.CharField(max_length=255)

    limit_id = models.CharField(max_length=255, blank=True, default="")

    status = models.CharField(
        max_length=255,
        choices=(
            ("pending", _("Pending")),
            ("running", _("Running")),
            ("completed", _("Completed")),
            ("failed", _("Failed")),
            ("cancelled", _("Cancelled")),
        ),
        default="pending",
    )

    param_json = models.TextField(
        blank=True, null=True, help_text="json containing args and kwargs"
    )
    error = models.TextField(
        blank=True,
        null=True,
        help_text="if the task failed will contain traceback or error info",
    )
    output = models.TextField(
        blank=True,
        null=True,
        help_text="task output - can also be used to store results",
    )

    timeout = models.IntegerField(
        null=True, blank=True, default=None, help_text="task timeout in seconds"
    )

    time = models.FloatField(default=0.0, help_text="time sepnt in seconds")

    source = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        default=worker_id,
        help_text="host id where task was triggered",
    )

    queue_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="task queue id (celery task id or orm worker id)",
    )

    parent = models.ForeignKey(
        "django_fullctl.Task",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )

    requeued = models.BooleanField(
        default=False,
        help_text="task was requeued",
    )

    # ownership

    user = models.ForeignKey(
        get_user_model(),
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text=_("Task was started by this user"),
    )

    org = models.ForeignKey(
        "django_fullctl.Organization",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text=_("Task belongs to this organization"),
    )

    class Meta:
        db_table = "fullctl_task"
        verbose_name = _("Task")
        verbose_name_plural = _("Tasks")

        # set indexes
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["op"]),
        ]

    class HandleRef:
        tag = "task"

    @classmethod
    def create_task(cls, *args, **kwargs):
        parent = kwargs.pop("parent", None)
        timeout = kwargs.pop("timeout", None)
        user = kwargs.pop("user", None)
        org = kwargs.pop("org", None)
        requeued = kwargs.pop("requeued", False)

        op = cls.HandleRef.tag

        if parent:
            parent = Task(id=parent.id)

        param = {"args": args or [], "kwargs": kwargs or {}}

        task = cls(
            op=op,
            param=param,
            status="pending",
            parent=parent,
            timeout=timeout,
            user=user,
            org=org,
            requeued=requeued,
        )
        task.limit_id = task.generate_limit_id

        try:
            task.clean()
        except TaskLimitError:
            if task.limit_action == LimitAction.silent:
                pass
            raise

        task.save()
        return task

    @classmethod
    def create_task_silent_limit(cls, *args, **kwargs):
        """
        Creates a task without raising an error if the limit is reached
        """

        try:
            return cls.create_task(*args, **kwargs)
        except TaskLimitError:
            pass

    @classmethod
    def last_run(cls, limit_id, age=0):
        """
        Returns the last time this task was run with the specified limit id

        Arguments:

        - limit_id (`mixed`)

        Keyword arguments:

        - age (`int`): max age in seconds

        Returns:

        - last run time (`datetime`) or `None` if it has not been run
        """

        qset = cls.objects.filter(op=cls.HandleRef.tag, limit_id=limit_id).exclude(
            status="failed"
        )

        if age != 0:
            qset = qset.filter(
                updated__gte=timezone.now() - datetime.timedelta(seconds=age)
            )

        qset = qset.order_by("-updated")

        task = qset.first()

        if task:
            return task.updated

        return None

    @property
    def generate_limit_id(self):
        return ""

    @property
    def limit(self):
        return self.task_meta_property("limit")

    @property
    def max_run_time(self):
        # check if task param kwargs has a max_run_time
        if "max_run_time" in self.param["kwargs"]:
            return self.param["kwargs"]["max_run_time"]

        return self.task_meta_property("max_run_time", settings.TASK_DEFAULT_MAX_AGE)

    @property
    def limit_action(self):
        return self.task_meta_property("limit_action", LimitAction.error)

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

    @property
    def result(self):
        """
        Returns the task result if task completed
        otherwise returns None

        You can type cast a result type by specifying
        the `result_type` property in `TaskMeta`
        """
        if self.status == "completed":
            typ = self.task_meta_property("result_type", str)
            return typ(self.output)
        return None

    @property
    def task_meta(self):
        """
        Returns TaskMeta if it exists, None otherwise
        """
        return getattr(self, "TaskMeta", None)

    @property
    def qualifies(self):
        """
        Checks if the environment qualifies to process
        this task.

        Will raise a WorkerUnqualified exception if not
        """

        task_meta = self.task_meta

        if not task_meta:
            return True

        qualifiers = getattr(task_meta, "qualifiers", [])

        for qualifier in qualifiers:
            if isinstance(qualifier, Dynamic):
                qualifier.set(self.dynamic_qualifier_id(qualifier))

            if not qualifier.check(self):
                raise WorkerUnqualified(self, qualifier)

        return True

    @property
    def name(self):
        return self.__class__.__name__

    def dynamic_qualifier_id(self, qualifier):
        return self.generate_limit_id

    def __str__(self):
        return f"{self.__class__.__name__}({self.id}): {self.param['args']}"

    def wait(self, timeout=None):
        """
        Waits for the task to be completed. This is a blocking action

        Keyword Arguments:

        - timeout(`int`): if specified timeout after n seconds
        """
        t = time.time()

        while True:
            if self.status == "completed":
                return
            time.sleep(0.1)
            self.refresh_from_db()

            if timeout and (time.time() - t).total_seconds > timeout:
                raise OSError("Task wait() timeout")

    async def async_wait(self, timeout=None):
        """
        Waits for a task to be completed with asyncio.
        This is a blocking action

        Keyword Arguments:

        - timeout(`int`): if specified timeout after n seconds
        """

        t = time.time()

        while True:
            if self.status == "completed":
                return
            await asyncio.sleep(0.1)
            sync_to_async(self.refresh_from_db)()
            if timeout and (time.time() - t).total_seconds > timeout:
                raise OSError("Task wait() timeout")

    def task_meta_property(self, name, default=None):
        """
        Returns a TaskMeta property value

        Arguments:

        - name(`str`) property name

        Keyword Arguments:

        - default(`mixed`): default value to return if property
        is not specified
        """
        task_meta = self.task_meta
        if not task_meta:
            return default

        return getattr(task_meta, name, default)

    def validate_limits(self):
        """
        Checks that creating a new instance of this task
        doesnt violate any limit we have specified
        """

        # no limit specified
        if self.limit is None:
            return

        op = self.HandleRef.tag
        limit_id = self.generate_limit_id

        count = self._meta.model.objects.filter(
            op=op, limit_id=limit_id, status__in=["pending", "running"]
        ).count()

        # if the count of currently pending / running instances of this
        # task is higher than the limit we specified we raise a
        # TaskLimitError
        if self.limit <= count:
            raise TaskLimitError()

    def clean(self):
        super().clean()
        try:
            if self.param_json:
                json.loads(self.param_json)
        except Exception as exc:
            raise ValidationError(f"Parameters could not be JSON encoded: {exc}")

        # this needs to be the last validation
        self.validate_limits()

    def cancel(self, reason):
        self._cancel(reason)

    def _cancel(self, reason):
        self.output = reason
        self.status = "cancelled"
        self.save()

    def _complete(self, output):
        self.output = output
        self.status = "completed"
        self.save()

    def _fail(self, error):
        self.error = error
        self.status = "failed"
        self.save()

    def _run(self):
        if self.status != "pending":
            raise TaskAlreadyStarted()

        if self.parent and self.parent.status != "completed":
            raise ParentTaskNotFinished()

        self.status = "running"
        self.save()
        t_start = time.time()
        try:
            param = self.param
            output = self.run(*param["args"], **param["kwargs"])
            t_end = time.time()
            self.time = t_end - t_start
            self._complete(output)
        except Exception:
            self._fail(traceback.format_exc())

    def run(self, *args, **kwargs):
        """extend in proxy model"""
        raise NotImplementedError()

    def run_command(self, command):
        # TODO this needs to capture output
        subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


class TaskClaim(HandleRefModel):

    """
    Used by a worker to claim a task

    Whenever a worker claims a task the worker first
    needs to create a taskclaim object for it.

    This object has a unique constraint on the task,
    preventing race conditions when several workers
    are polling and claiming tasks asynchronously.
    """

    task = models.OneToOneField(Task, on_delete=models.CASCADE)
    worker_id = models.CharField(max_length=255)

    class Meta:
        db_table = "fullctl_task_claim"
        verbose_name = _("Claimed Task")
        verbose_name_plural = _("Claimed Tasks")

    class HandleRef:
        tag = "task_claim"


class TaskSchedule(HandleRefModel):

    """
    Implements delayed and repeated task execution
    """

    # schedule config

    interval = models.PositiveIntegerField(
        help_text=_("Interval in seconds"), null=False, blank=False
    )

    repeat = models.BooleanField(
        help_text=_("Repeat task"),
        default=False,
    )

    schedule = models.DateTimeField(
        help_text=_("Next scheduled execution"),
        null=False,
        blank=False,
        db_index=True,
    )

    description = models.CharField(max_length=255, null=True, blank=True)

    # task config

    task_config = models.JSONField(null=False, blank=False, help_text=_("Task setup"))

    tasks = models.ManyToManyField(Task, blank=True)

    # ownership

    user = models.ForeignKey(
        get_user_model(),
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text=_("Task schedule was started by this user"),
    )

    org = models.ForeignKey(
        "django_fullctl.Organization",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        help_text=_("Task schedule belongs to this organization"),
    )

    class Meta:
        db_table = "fullctl_task_schedule"
        verbose_name = _("Scheduled Task")
        verbose_name_plural = _("Scheduled Tasks")

    class HandleRef:
        tag = "task_schedule"

    def reschedule(self):
        self.schedule = timezone.now() + datetime.timedelta(seconds=self.interval)
        self.save()

    def are_limited_tasks_pending(self):
        """
        Checks if there are currently any pending limited tasks
        """
        from fullctl.django.tasks.orm import specify_task

        task_configs = self.task_config.get("tasks", [])

        for task_config in task_configs:
            op = task_config.get("op")
            # TODO: can we really safely assume that the first arg is the limit_id?
            try:
                limit_id = task_config.get("param").get("args")[0]
            except IndexError:
                continue

            tasks = Task.objects.filter(
                op=op, limit_id=limit_id, status__in=["pending", "running"]
            )

            task_object = tasks.first()
            if not task_object:
                continue

            task = specify_task(task_object)
            # if the count of currently pending / running instances of this
            # task is higher than the limit we return True
            if tasks and (task.task_meta_property("limit") <= tasks.count()):
                return True

        return False

    def spawn_tasks(self):
        # first check that there isnt currently a task pending on the schedule already

        if self.are_limited_tasks_pending():
            return []

        for task in self.tasks.all():
            if task.status in ["pending", "running"]:
                raise TaskAlreadyStarted()

        tasks = fullctl.django.tasks.create_tasks_from_json(
            self.task_config,
            user=self.user,
            org=self.org,
        )

        if self.repeat:
            self.reschedule()
        else:
            self.status = "deactivated"
            self.save()

        for task in tasks:
            self.tasks.add(task)

        return tasks


class Monitor(HandleRefModel):
    email = models.EmailField(
        null=True, blank=True, help_text=_("Primary alert notification email")
    )

    class Meta:
        abstract = True

    @property
    def is_enabled(self):
        if not self.task_schedule_id:
            return False

        return self.task_schedule.status == "ok"

    @property
    def schedule_task_config(self):
        return {}

    @property
    def schedule_interval(self):
        return 3600

    @property
    def schedule_description(self):
        return self.__class__.__name__

    @property
    def require_task_schedule(self):
        if not self.task_schedule:
            org = self.instance.org
            self.task_schedule = TaskSchedule.objects.create(
                org=org,
                task_config=self.schedule_task_config,
                description=self.schedule_description,
                repeat=True,
                interval=self.schedule_interval,
                schedule=timezone.now(),
            )
            self.save()

        return self.task_schedule

    def save(self, **kwargs):
        super().save(**kwargs)

        if not self.task_schedule:
            self.require_task_schedule

    def delete(self, **kwargs):
        super().delete(**kwargs)

        try:
            if self.task_schedule.id:
                self.task_schedule.delete()
        except TaskSchedule.DoesNotExist:
            pass


@fullctl.django.tasks.register
class CallCommand(Task):

    """
    Django management tasks
    """

    class Meta:
        proxy = True

    class HandleRef:
        tag = "task_callcommand"

    def run(self, *args, **kwargs):
        """
        Executes a django management command
        """

        out = StringIO()
        call_command(commit=True, *args, **kwargs, stdout=out)
        return f"{out.getvalue()}"
