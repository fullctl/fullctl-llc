import os
import socket

from django.conf import settings


def worker_id():
    """
    Returns the worker id for this instance

    This can be specified manually through the
    `TASK_ORM_WORKER_ID` setting

    If unspecified will default to hostname:pid
    """

    return getattr(
        settings, "TASK_ORM_WORKER_ID", f"{socket.gethostname()}:{os.getpid()}"
    )
