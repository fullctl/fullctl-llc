"""
Task qualifiers to facilitate selective task processing
"""

from django.conf import settings

__all__ = [
    "Base",
    "Setting",
    "SettingUnset",
    "ConcurrencyLimit",
    "Dynamic",
]


class Base:

    """
    Base task qualifier interface

    Extend this
    """

    # if the qualifier fails to qualify a task
    # we will not reattempt qualifying the task
    # for this many seconds
    recheck_time = 5

    def check(self, task):
        raise NotImplementedError()

    def ids(self, task):
        return {}


class Dynamic(Base):
    def set(self, *args, **kwargs):
        raise NotImplementedError()


class Setting(Base):
    """
    Requires there to be specific settings value set
    in order_history for the task to qualify for processing
    on this instance
    """

    def __init__(self, setting, value):
        self.setting = setting
        self.value = value

    def __str__(self):
        return f"{self.__class__.__name__} {self.setting}"

    def check(self, task):
        try:
            _value = getattr(settings, self.setting)
        except AttributeError:
            return False

        # if a callback was passed to self.value
        # run the settings value through it and return
        # the result
        if callable(self.value):
            b = self.value(_value)
            if not isinstance(b, bool):
                raise TypeError("Base value callbacks should return a boolean")
            return b

        # otherwise compare values
        return self.value == _value


class SettingUnset(Base):

    """
    Requires a specific setting to be UNSET
    """

    def __init__(self, setting):
        self.setting = setting

    def __str__(self):
        return f"{self.__class__.__name__} {self.setting}"

    def check(self, task):
        try:
            getattr(settings, self.setting)
        except AttributeError:
            return True
        return False


class ConcurrencyLimit(Base):

    """
    Limits how many instance of the task can be worked on at
    the same time
    """

    def __init__(self, limit):
        self.limit = limit

    def __str__(self):
        return f"{self.__class__.__name__} {self.limit}"

    def check(self, task):
        return (
            task.__class__.objects.filter(
                status__in=["pending", "running"], queue_id__isnull=False, op=task.op
            ).count()
            < self.limit
        )
