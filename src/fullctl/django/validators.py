import re

from django.core.exceptions import ValidationError


def validate_alphanumeric(value):
    """
    validates a value to only contain alphanumeric characters, dashes
    or underscores

    Argument(s):

        - value(str)

    Raises:

        - ValidationError: on failed validation
    """

    if re.search("[^a-zA-Z0-9-_]", value):
        raise ValidationError("value can only contain a-Z, 0-9, ,- ,_")


def validate_alphanumeric_list(value):
    """
    validates a list to only contain alphanumeric characters, dashes
    or underscores

    Argument(s):

        - value(list|str): if a str is supplied, it will be split using `,`
          as a separator

    Raises:

        - ValidationError: on failed validation
    """

    if not isinstance(value, list):
        value = value.split(",")

    for item in value:
        validate_alphanumeric(item)
