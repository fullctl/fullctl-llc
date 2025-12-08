import functools
from collections.abc import Generator, Iterable
from typing import Any


def rgetattr(obj, attr, *args):
    def _getattr(obj, attr):
        return getattr(obj, attr, *args)

    return functools.reduce(_getattr, [obj] + attr.split("."))


def rsetattr(obj, attr, val):
    pre, _, post = attr.rpartition(".")
    return setattr(rgetattr(obj, pre) if pre else obj, post, val)


def chunk_list(
    data: Iterable[Any], chunk_size: int
) -> Generator[Iterable[Any], None, None]:
    """
    Splits a list or tuple or generator into chunks of a specified size.

    :param data: The list of objects to split.
    :param chunk_size: The size of each chunk.
    :return: A generator yielding chunks of the specified size.
    """
    for i in range(0, len(data), chunk_size):
        yield data[i : i + chunk_size]
