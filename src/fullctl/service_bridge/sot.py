"""
Retrieve data from the source of truth

Currently this covers internet exchange member information which either
exists in pdbctl (peeringdb data) or ixctl, but could be extended on
further down the line
"""

import fullctl.service_bridge.ixctl as ixctl
import fullctl.service_bridge.pdbctl as pdbctl
import fullctl.service_bridge.peerctl as peerctl
from fullctl.service_bridge.client import ServiceBridgeError

SOURCE_MAP = {
    "member": {"pdbctl": pdbctl.NetworkIXLan, "ixctl": ixctl.InternetExchangeMember},
    "port_info": {"pdbctl": pdbctl.NetworkIXLan, "ixctl": ixctl.InternetExchangeMember},
    "ix": {"pdbctl": pdbctl.InternetExchange, "ixctl": ixctl.InternetExchange},
    "as_set": {"pdbctl": pdbctl.Network, "peerctl": peerctl.Network},
}


class ReferenceNotFoundError(KeyError):
    pass


def get_ref_definition(obj):

    """
    Will return the reference tag and id reference field name
    as a tuple.

    This will use django HandleRef ref tags if they exist.

    id reference field name will be obtained from a `ref_field` attribute
    that should either exist on HandleRef meta class or on the object
    itself. Will default to `id` if missing.
    """

    if hasattr(obj, "HandleRef"):
        ref_tag = obj.HandleRef.tag
        ref_field = getattr(obj.HandleRef, "ref_field", "id")
    elif hasattr(obj, "ref_tag"):
        ref_tag = obj.ref_tag
        ref_field = getattr(obj, "ref_field", "id")
    else:
        raise AttributeError(f"Cannot find ref tag on object: {obj}")

    return ref_tag, ref_field


class ReferenceMixin:

    """
    Mixin class to use with django models (but also work with other object
    types)

    Needs to specify a `ref_id` attribute that should hold a reference to
    a service bridge data object in the format of `{source}:{id}`.

    Example: `ixctl.137`

    Needs to specify a `ref_tag` attribute, either through HandleRef
    or directly on the object. ref_tag needs to exist SOURCE_MAP
    """

    @classmethod
    def ref_bridge(cls, source):
        """Returns service bridge instance"""
        ref_tag, ref_field = get_ref_definition(cls)
        return SOURCE_MAP[ref_tag].get(source)()

    @property
    def ref_parts(self):
        """Return reference source name and id as a tuple"""
        src, _id = self.ref_id.split(":")
        return (src, int(_id))

    @property
    def ref_source(self):
        """Return reference source name"""
        return self.ref_parts[0]

    @property
    def ref(self):
        """Return reference object (DataObject)"""
        if hasattr(self, "_ref"):
            return self._ref

        ref_tag, ref_field = get_ref_definition(self)
        source, id = self.ref_parts
        bridge = SOURCE_MAP[ref_tag].get(source)()

        filters = {ref_field: id}

        self._ref = bridge.first(**filters)

        if not self._ref:
            raise ReferenceNotFoundError()

        return self._ref

    def ref_objects(self, **kwargs):
        """
        Return reference objects (DataObject instances) according to filters
        specified in kwargs
        """
        return self.ref_bridge(self.ref_source).objects(**kwargs)


class SourceOfTruth:
    sources = []
    key = ("id",)

    def object(self, *args, **kwargs):
        for source, params in self.sources:

            client = source()

            # source host not specified, skip
            # TODO: error when no source hosts are specified ?
            if not client.host:
                continue

            kwargs.update(params)
            kwargs["raise_on_notfound"] = False
            try:
                return client.object(*args, **kwargs)
            except ServiceBridgeError as exc:
                if exc.status == 404:
                    continue
                raise
        if kwargs.get("raise_on_notfound"):
            raise KeyError("Object does not exist")

    def objects(self, **kwargs):

        _result = []

        for source, params in self.sources:

            client = source()

            # source host not specified, skip
            # TODO: error when no source hosts are specified ?
            if not client.host:
                continue

            kwargs.update(params)
            try:
                for obj in client.objects(**kwargs):
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


class ASSet(SourceOfTruth):

    sources = [(peerctl.Network, {"has_as_set": 1}), (pdbctl.Network, {})]

    def filter_source_of_truth(self, networks):

        asn_map = {}
        filtered = []

        for net in networks:
            if net.asn not in asn_map:
                filtered.append(net)
                asn_map[net.asn] = net

        return filtered
