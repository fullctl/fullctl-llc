import ipaddress
import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

# valid IRR source identifiers
# reference: http://www.irr.net/docs/list.html
IRR_SOURCE = (
    "AFRINIC",
    "ALTDB",
    "APNIC",
    "ARIN",
    "BELL",
    "BBOI",
    "CANARIE",
    "IDNIC",
    "JPIRR",
    "LACNIC",
    "LEVEL3",
    "NESTEGG",
    "NTTCOM",
    "PANIX",
    "RADB",
    "REACH",
    "RIPE",
    "TC",
)


def validate_ip4(value):
    try:
        ipaddress.IPv4Address(value)
    except ipaddress.AddressValueError:
        raise ValidationError("Invalid IPv4 Address")


def validate_ip6(value):
    try:
        ipaddress.IPv6Address(value)
    except ipaddress.AddressValueError:
        raise ValidationError("Invalid IPv6 Address")


def validate_prefix(value):
    try:
        ipaddress.ip_network(value)
    except ValueError as exc:
        raise ValidationError(f"Invalid prefix: {exc}")


def validate_masklength_range(value):
    if not re.match(r"^([0-9]+\.\.[0-9]+|exact)$", value):
        raise ValidationError("Needs to be [0-9]+..[0-9]+ or 'exact'")


def validate_as_set(value):
    """
    Validates irr as-set string
    - the as-set/rs-set name has to conform to RFC 2622 (5.1 and 5.2)
    - the source may be specified by SOURCE::AS-SET
    - multiple values must be separated by either comma, space or comma followed by space
    Arguments:
    - value: irr as-set string
    Returns:
    - str: validated irr as-set string
    """

    if not isinstance(value, str):
        raise ValueError(_("IRR AS-SET value must be string type"))

    # split multiple values

    # normalize value separation to commas
    value = value.replace(", ", ",")
    value = value.replace(" ", ",")

    validated = []

    # validate
    for item in value.split(","):
        item = item.upper()
        source = None
        as_set = None

        # <source>::<name>
        parts_match = re.match(r"^(\w+)::([\w\d\-:]+)$", item)
        if parts_match:
            source = parts_match.group(1)
            as_set = parts_match.group(2)
        else:
            sourceless_match = re.match(r"^([\w\d\-:]+)$", item)
            if not sourceless_match:
                raise ValidationError(
                    _(
                        "Invalid formatting: {} - should be AS-SET, ASx, SOURCE::AS-SET"
                    ).format(item)
                )
            as_set = sourceless_match.group(1)

        if source and source not in IRR_SOURCE:
            raise ValidationError(_("Unknown IRR source: {}").format(source))

        # validate set name and as hierarchy
        as_parts = as_set.split(":")

        set_found = False
        types = []

        for part in as_parts:
            match_set = re.match(r"^(AS|RS)-[\w\d\-]+$", part)
            match_as = re.match(r"^(AS)[\d]+$", part)

            # set name found

            if match_set:
                set_found = True
                types.append(match_set.group(1))
            elif not match_as:
                raise ValidationError(
                    _(
                        "Invalid formatting: {} - should be RS-SET, AS-SET or AS123"
                    ).format(part)
                )

        if len(list(set(types))) > 1:
            raise ValidationError(
                _("All parts of an hierarchical name have to be of the same type")
            )

        if not set_found and len(as_parts) > 1:
            raise ValidationError(
                _("At least one component must be an actual set name")
            )

        validated.append(item)

    return ", ".join(validated)
