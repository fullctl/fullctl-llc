from collections import namedtuple

import pytest
from django.core.exceptions import ValidationError

from fullctl.django.inet import validators


def test_validate_ip4(ipaddrs):
    validators.validate_ip4(ipaddrs.IPADDRESS4)

    with pytest.raises(ValidationError):
        validators.validate_ip4(ipaddrs.IPADDRESS6)

    with pytest.raises(ValidationError):
        validators.validate_ip4(ipaddrs.INVALID_IPADDRESS4)


def test_validate_ip6(ipaddrs):
    validators.validate_ip6(ipaddrs.IPADDRESS6)

    with pytest.raises(ValidationError):
        validators.validate_ip6(ipaddrs.IPADDRESS4)

    with pytest.raises(ValidationError):
        validators.validate_ip6(ipaddrs.INVALID_IPADDRESS6)


def test_validate_prefix(ipaddrs):

    validators.validate_prefix(ipaddrs.PREFIX)
    validators.validate_prefix(ipaddrs.NETMASK)

    with pytest.raises(ValidationError) as execinfo:
        validators.validate_prefix(ipaddrs.INVALID_PREFIX)

    assert "Invalid prefix" in str(execinfo.value)


def test_validate_masklength_range(ipaddrs):

    validators.validate_masklength_range("32..128")
    validators.validate_masklength_range("exact")

    with pytest.raises(ValidationError) as execinfo:
        validators.validate_masklength_range("123")

    assert "Needs to be [0-9]+..[0-9]+ or 'exact'" in str(execinfo.value)


@pytest.fixture
def ipaddrs():
    Ipaddresses = namedtuple(
        "Ipaddresses",
        "IPADDRESS4 IPADDRESS6 INVALID_IPADDRESS4 INVALID_IPADDRESS6 PREFIX NETMASK INVALID_PREFIX INVALID_NETMASK",
    )
    return Ipaddresses(
        "192.168.0.1",
        "2001:db8::1000",
        "192.350.0.1",
        "2001:xyz::1000",
        "192.168.0.0/28",
        "192.168.0.0/255.255.255.0",
        "192.168.0.0/999",
        "192.168.0.0/10000.255.255.255",
    )
