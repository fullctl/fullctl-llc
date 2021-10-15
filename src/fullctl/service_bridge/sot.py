"""
Retrieve data from the source of truth

Currently this covers internet exchange member information which either
exists in pdbctl (peeringdb data) or ixctl, but could be extended on
further down the line
"""

import fullctl.service_bridge.ixctl as ixctl
import fullctl.service_bridge.pdbctl as pdbctl
from fullctl.service_bridge.client import ServiceBridgeError

SOURCE_MAP = {
    "member": {"pdbctl": pdbctl.NetworkIXLan, "ixctl": ixctl.InternetExchangeMember},
    "ix": {"pdbctl": pdbctl.InternetExchange, "ixctl": ixctl.InternetExchange},
}


class SourceOfTruth:
    sources = []
    key = ("id",)

    def make_key(self, obj):
        return (getattr(obj, k) for k in self.key)

    def object(self, *args, **kwargs):
        for source, params in self.sources:
            kwargs.update(params)
            kwargs["raise_on_notfound"] = False
            try:
                return source().object(*args, **kwargs)
            except ServiceBridgeError as exc:
                if exc.status == 404:
                    continue
                raise
        if kwargs.get("raise_on_notfound"):
            raise KeyError("Object does not exist")

    def objects(self, **kwargs):

        _result = []

        for source, params in self.sources:
            kwargs.update(params)
            try:
                for obj in source().objects(**kwargs):
                    _result.append(obj)

            except ServiceBridgeError as exc:
                if exc.status == 404:
                    continue
                raise

        return self.filter_source_of_truth(_result)

    def first(self, **kwargs):
        for o in self.objects(**kwargs):
            return o

    def filter_source_of_truth(self, objects):
        return objects

    def join_relationships(self, objects):
        return objects


class InternetExchangeMember(SourceOfTruth):

    sources = [
        (ixctl.InternetExchangeMember, {"sot": True}),
        (pdbctl.NetworkIXLan, {}),
    ]

    def filter_source_of_truth(self, members):
        filtered = []
        pdb_ixctl_map = {}

        for member in members:
            if member.source == "ixctl":
                pdb_ixctl_map[member.pdb_ix_id] = True

        for member in members:
            if member.source == "pdbctl" and member.ix_id in pdb_ixctl_map:
                continue
            filtered.append(member)

        return filtered
