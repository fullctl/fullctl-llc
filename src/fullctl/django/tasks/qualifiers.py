"""
Task qualifiers to facilitate selective task processing
"""

from django.conf import settings


class Base:

    """
    Base task qualifier interface

    Extend this
    """

    def check(self, task):
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
