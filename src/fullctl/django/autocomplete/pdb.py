from dal import autocomplete

import fullctl.service_bridge.pdbctl as pdbctl


class peeringdb_ix(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.q:
            return []
        qs = [o for o in pdbctl.InternetExchange().objects(q=self.q)]
        return qs

    def get_result_label(self, ix):
        return ix.name


class peeringdb_asn(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = list(pdbctl.Network().objects(q_asn=self.q))
        return qs

    def get_result_label(self, item):
        return f"AS{item.asn} {item.name}"

    def get_result_value(self, item):
        return item.asn


class peeringdb_net(peeringdb_asn):
    def get_queryset(self):
        qs = list(pdbctl.Network().objects(q=self.q, limit=50))
        return qs


class peeringdb_org(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = pdbctl.Organization().objects(q=self.q)
        return qs
