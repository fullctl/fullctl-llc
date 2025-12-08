"""
functions to calculate api usage per org for a metered service
"""

REGISTERED = {}


def register(cls):
    REGISTERED[cls.Meta.name] = cls


class UsageMetric:
    """
    Base usage metric class, all other usage metrics
    should extend this
    """

    class Meta:
        name = "base"

    def __init__(self, org):
        self.org = org

    def calc(self, start, end):
        raise NotImplementedError()
