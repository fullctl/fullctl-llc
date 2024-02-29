"""
Defines an extendible healthcheck process for FullCtl services.
"""
from django.db import connection

__all__ = [
    "register",
    "check_all",
    "HEALTH_CHECKS",
]

# holds all registered health checks
HEALTH_CHECKS = {}


class register:
    """
    Registers a health check function.

    The function will be called with no arguments.

    It should raise an exception if the check fails.
    """

    def __init__(self, name):
        self.name = name

    def __call__(self, func):
        HEALTH_CHECKS[self.name] = func
        return func


def check_all() -> dict:
    """
    Run all registered health checks.
    """
    results = {}
    for name, func in HEALTH_CHECKS.items():
        results[name] = func()

    return results


@register("db")
def health_check_db():
    """
    Performs a simple database version query
    """
    # postgresql
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute("SELECT version()")
    # sqlite
    elif connection.vendor == "sqlite":
        with connection.cursor() as cursor:
            cursor.execute("SELECT sqlite_version()")
    # fallback to default (postgresql, in case vendor naming changes in the future)
    else:
        with connection.cursor() as cursor:
            cursor.execute("SELECT version()")
