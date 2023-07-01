"""
Contains a bunch of concrete models to help testing
"""

from django.db import models
from fullctl.django.models import Task
from fullctl.django.tasks import qualifiers, register
import fullctl.django.models.abstract.meta as meta

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
        import time

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