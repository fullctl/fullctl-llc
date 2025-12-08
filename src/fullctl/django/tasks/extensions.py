"""
Allows functions to be registered by an extension handle

Tasks can then call callbacks by their handle, allowing fullctl service
plugins to augment existing Task Operations with custom functionality.
"""

import functools
from typing import Callable

from django.conf import settings

__all__ = ["register", "call"]

REGISTERED_EXTENSIONS = {}


class register:
    """
    Decorator to register a function to be called when the handle is called

    Arguments:
    - handle: str - The handle to register the function to. This is made up of the service tag, task operation and event
    - condition: callable - A function that should return True if the function should be called, False otherwise
    """

    def __init__(self, handle: str, condition: Callable = None):
        self.handle = handle
        self.condition = condition

    def __call__(self, func: Callable):
        _register(self.handle, func, self.condition)
        return func


def _register(handle: str, func: Callable, condition: Callable = None):
    """
    Register a function to be called when the handle is called

    Arguments:
    - handle: str - The handle to register the function to. This is made up of the service tag, task operation and event
    - func: callable - The function to call when the handle is called
    - condition: callable - A function that should return True if the function should be called, False otherwise

    Example:
    ```
    register("my_service.my_task", my_func)
    ```
    """

    # if callable is provided, wrap the function in a function
    # that will only call the function if the condition is met

    if condition:

        @functools.wraps(func)
        def wrapper(task, *args, **kwargs):
            if condition(task):
                return func(task, *args, **kwargs)

        REGISTERED_EXTENSIONS.setdefault(handle, []).append(wrapper)
    else:
        REGISTERED_EXTENSIONS.setdefault(handle, []).append(func)


def call(task, event: str = None, result: dict | None = None, *args, **kwargs):
    """
    Call all registered functions for the given task handle

    Arguments:
    - task: Task - The task object that is being called
    - event: str - The event that is being called. Optional
    - result: dict - The result of the task. Optional
    - *args: passed through as is to the registered functions
    - **kwargs: passed through as is to the registered functions
    """

    # handle is made from settings.SERVICE_TAG + "." + task.op + "." + event (if event is not None)

    handle = f"{settings.SERVICE_TAG}.{task.op}"

    if result is None:
        result = {}

    if event:
        handle += f".{event}"

    for func in REGISTERED_EXTENSIONS.get(handle, []):
        _result = func(task, result=result, *args, **kwargs)
        if isinstance(_result, dict):
            result.update(_result)
