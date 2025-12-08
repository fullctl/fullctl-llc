import ipaddress

import pytest

from fullctl.django.inet.util import ipv6_from_ipv4


@pytest.mark.parametrize(
    "prefix, ipv4_address, expected_ipv6",
    [
        ("2001:504:41:110::/64", "206.41.110.22", "2001:504:41:110::22"),
        ("2001:db8::/64", "10.10.10.32", "2001:db8::32"),
        ("2001:0:0:1::/64", "10.10.10.255", "2001:0:0:1::255"),
    ],
)
def test_ipv6_from_ipv4(prefix, ipv4_address, expected_ipv6):
    result = ipv6_from_ipv4(prefix, ipv4_address)
    assert result == ipaddress.IPv6Address(expected_ipv6)


@pytest.mark.parametrize(
    "prefix, ipv4_address",
    [
        ("2001:504:41:110::/64", ipaddress.IPv4Address("206.41.110.22")),
        (ipaddress.IPv6Network("2001:db8::/64"), "192.0.2.33"),
        (ipaddress.IPv6Network("2001:0:0:1::/64"), ipaddress.IPv4Address("10.0.0.1")),
    ],
)
def test_ipv6_from_ipv4_input_types(prefix, ipv4_address):
    result = ipv6_from_ipv4(prefix, ipv4_address)
    assert isinstance(result, ipaddress.IPv6Address)


def test_ipv6_from_ipv4_invalid_prefix():
    with pytest.raises(ipaddress.AddressValueError):
        ipv6_from_ipv4("invalid_prefix", "192.0.2.1")


def test_ipv6_from_ipv4_invalid_ipv4():
    with pytest.raises(ipaddress.AddressValueError):
        ipv6_from_ipv4("2001:db8::/64", "invalid_ip")
