"""
Metric Model Module.
"""

from django.db import models

from .base import HandleRefModel

__all__ = [
    "MetricModel",
]


class MetricModel(HandleRefModel):
    """
    Metric model stores data points related to a specific measurement.

    The Metric model is designed to store a set of related metrics within a
    single JSON object. Each metric can have multiple nested attributes,
    allowing for a flexible structure that can accommodate various types of
    measurements values.

    Attributes:
        data (JSONField): A JSON object storing various metrics.
        timestamp (DateTimeField): The timestamp when the metric was recorded. Defaults to the current time.

    Methods:
        __str__(): Returns a string representation of the Metric instance, usually for debugging or admin interface display.
    """

    data = models.JSONField(help_text="A JSON object containing various metrics.")
    timestamp = models.DateTimeField(
        auto_now=True, help_text="The time at which this metric was recorded."
    )

    class Meta:
        """
        Meta options for the Metric model.

        Provides additional information about the Metric model, including:
        - ordering: The default ordering for queries made against this model (by timestamp descending).
        """

        abstract = True
        ordering = ["-timestamp"]
