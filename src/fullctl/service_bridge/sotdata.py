"""
Retrieve data from the source of truth

Currently this covers internet exchange member information which either
exists in pdbctl (peeringdb data) or ixctl, but could be extended on
further down the line
"""

class SoTData:
    pass

class InternetExchangeMember(SoTData):

    sources = [
        ("ixctl", "member"),
        ("pdbctl", "netixlan"),
    ]


