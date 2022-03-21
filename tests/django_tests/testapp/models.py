"""
Contains a bunch of concrete models to help testing
"""

from fullctl.django.models import Task
from fullctl.django.tasks import qualifiers, register


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
