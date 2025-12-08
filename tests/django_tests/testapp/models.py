"""
Contains a bunch of concrete models to help testing
"""

import time

from django.db import models

import fullctl.django.models.abstract.meta as meta
from fullctl.django.models import Task, TaskHeartbeat
from fullctl.django.models.abstract.base import SlugModel
from fullctl.django.tasks import qualifiers, register
from fullctl.django.tasks.context import check_task_cancelled


@register
class TestTask(Task):
    class Meta:
        proxy = True

    class HandleRef:
        tag = "task_test"

    class TaskMeta:
        result_type = int

    def run(self, a, b, *args, **kwargs):
        return a + b


class TestTaskHeartbeat(TaskHeartbeat):
    class Meta:
        proxy = True

    class HandleRef:
        tag = "task_test_heartbeat"


class UnregisteredTestTask(Task):
    class Meta:
        proxy = True

    class HandleRef:
        tag = "unregistered_task_test"

    class TaskMeta:
        result_type = int

    def run(self, a, b, *args, **kwargs):
        return a + b


@register
class TestTaskWithMaxRunTime(Task):
    class Meta:
        proxy = True

    class HandleRef:
        tag = "task_max_run_time_test"

    class TaskMeta:
        result_type = int
        max_run_time = 3600  # seconds

    def run(self, a, b, *args, **kwargs):
        return a + b


@register
class ParentTestTask:
    class Meta:
        proxy = True

    class HandleRef:
        tag = "task_parent_test"

    def run(self, a, *args, **kwargs):
        b = int(self.parent.output)
        return a + b


@register
class QualifierTestTask(TestTask):
    class Meta:
        proxy = True

    class HandleRef:
        tag = "task_qualifier_test"

    class TaskMeta:
        qualifiers = [
            qualifiers.Setting("TEST_QUALIFIER", True),
            qualifiers.SettingUnset("TEST_UNSET_QUALIFIER"),
        ]


@register
class LongTask(TestTask):
    class Meta:
        proxy = True

    class HandleRef:
        tag = "task_long"

    def run(self, a, b, *args, **kwargs):

        time.sleep(1)
        return a + b


@register
class LimitedTask(Task):
    class Meta:
        proxy = True

    class HandleRef:
        tag = "task_limited"

    class TaskMeta:
        limit = 1

    def run(self, *args, **kwargs):
        return True


@register
class LimitedTaskWithLimitId(LimitedTask):
    class Meta:
        proxy = True

    class HandleRef:
        tag = "task_limited_2"

    class TaskMeta:
        limit = 1

    @property
    def generate_limit_id(self):
        return self.param["args"][0]


@register
class FailingTask(Task):
    class Meta:
        proxy = True

    class HandleRef:
        tag = "task_failing"

    class TaskMeta:
        result_type = int

    def run(self, *args, **kwargs):
        return int("string")


@register
class CancellableTask(Task):
    """
    Test task that can be cancelled during execution.
    Simulates a long-running task by processing items in a loop.
    """

    class Meta:
        proxy = True

    class HandleRef:
        tag = "task_cancellable"

    class TaskMeta:
        result_type = int

    def run(self, iterations=10, *args, **kwargs):
        """
        Run a loop that checks for cancellation before each iteration.

        Args:
            iterations: Number of iterations to perform
        """

        processed = 0
        for i in range(iterations):
            # Check for cancellation before processing each iteration
            check_task_cancelled()
            time.sleep(0.1)
            processed += 1
        return processed


@register
class NonCancellableTask(Task):
    """
    Test task that doesn't check for cancellation.
    Will run to completion even if cancelled.
    """

    class Meta:
        proxy = True

    class HandleRef:
        tag = "task_non_cancellable"

    class TaskMeta:
        result_type = int

    def run(self, iterations=5, *args, **kwargs):
        """Run without any cancellation checks"""

        for i in range(iterations):
            time.sleep(0.1)
        return iterations


class Data(meta.Data):
    """
    Concrete implementation of Data model
    """

    target = models.CharField(max_length=255)

    class Meta:
        verbose_name = "Data"
        verbose_name_plural = "Data"
        db_table = "test_meta_data"

    class Config:
        type = "test"
        source_name = "test"
        period = 12 * 3600  # Specify the historic period in seconds

    class HandleRef:
        tag = "data"


class Response(meta.Response):
    """
    Maintains a cache for third party data responses
    """

    request = models.OneToOneField(
        "Request",
        on_delete=models.CASCADE,
        related_name="response",
    )

    class Meta:
        db_table = "test_meta_respnse"
        verbose_name_plural = "Response cache"
        verbose_name = "Response cache"

    class HandleRef:
        tag = "response"

    class Config:
        meta_data_cls = Data


class Request(meta.Request):
    """
    Concrete implementation of Request model
    """

    target = models.CharField(max_length=255)

    class Meta:
        verbose_name = "Request"
        verbose_name_plural = "Requests"
        db_table = "test_meta_request"

    class HandleRef:
        tag = "request"

    class Config:
        meta_data_cls = Data
        source_name = "test"
        target_field = "target"
        cache_expiry = 86400

    @classmethod
    def target_to_url(cls, target):
        """
        override this to handle converting a target to a requestable url
        """
        return target  # Simply return the target as the URL


class ModelWithSlug(SlugModel):
    """
    A model with a slug
    """

    class Meta:
        db_table = "test_slug"

    class HandleRef:
        tag = "slug"
