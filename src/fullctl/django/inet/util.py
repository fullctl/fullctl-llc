import ipaddress

from django.core.exceptions import ObjectDoesNotExist

from fullctl.django.inet.exceptions import PdbNotFoundError

__all__ = [
    "pdb_lookup",
    "get_client_ip",
    "ipv6_from_ipv4",
]


def pdb_lookup(cls, **filters):
    try:
        return cls.objects.get(**filters)
    except ObjectDoesNotExist:
        raise PdbNotFoundError(cls.handleref.tag, filters)


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


def ipv6_from_ipv4(
    prefix: ipaddress.IPv6Network | str, ipv4_address: ipaddress.IPv4Address | str
) -> ipaddress.IPv6Address:
    """
    Takes an IPv6 prefix and an IPv4 address and returns the IPv6 address that corresponds to the IPv4 address by taking the last octet of the IPv4 address and applying it to the IPv6 address.

    So if you have an IPv6 prefix of 2001:504:41:110::/64 and an IPv4 address of 206.41.110.22
    The function will return 2001:504:41:110::22
    """
    # Convert prefix and IPv4 address to appropriate types if they're strings
    if isinstance(prefix, str):
        prefix = ipaddress.IPv6Network(prefix)
    if isinstance(ipv4_address, str):
        ipv4_address = ipaddress.IPv4Address(ipv4_address)

    # Get the integer representations
    ipv6_int = int(prefix.network_address)
    ipv4_int = int(ipv4_address)

    # Get the last octet of the IPv4 address
    last_octet = ipv4_int & 0xFF

    # Convert the last octet to hexadecimal, keeping its decimal value
    last_octet_hex = int(f"{last_octet:02d}", 16)

    # Clear the last 8 bits of the IPv6 address and add the converted last octet
    new_ipv6_int = (ipv6_int & ~0xFF) | last_octet_hex

    return ipaddress.IPv6Address(new_ipv6_int)
