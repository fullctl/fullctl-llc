import pytest
from django.core.exceptions import ValidationError

from fullctl.django import validators


def test_validate_alphanumeric():
    validators.validate_alphanumeric("1a_2B-3c4D")

    with pytest.raises(ValidationError) as execinfo:
        validators.validate_alphanumeric(".")

    assert "value can only contain a-Z, 0-9, ,- ,_" in str(execinfo.value)


def test_validate_alphanumeric_list():
    validators.validate_alphanumeric_list(["1a_2B-3c4D", "5f_6G-7h8L", "9m_10N-11o12P"])
    validators.validate_alphanumeric_list("1a_2B-3c4D,5f_6G-7h8L,9m_10N-11o12P")

    with pytest.raises(ValidationError) as execinfo:
        validators.validate_alphanumeric_list("1a_2B-3c4D,5f_6G-7h8L,9m_10N-11o12P.")

    assert "value can only contain a-Z, 0-9, ,- ,_" in str(execinfo.value)
