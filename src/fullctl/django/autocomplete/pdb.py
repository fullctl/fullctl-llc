import django_peeringdb.models.concrete as pdb_models
from dal import autocomplete


class peeringdb_ix(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = pdb_models.IXLan.objects.filter(status="ok")
        if self.q:
            qs = qs.filter(ix__name__istartswith=self.q)
        return qs

    def get_result_label(self, ixlan):
        if ixlan.name:
            return f"{ixlan.ix.name} - {ixlan.name}"
        return ixlan.ix.name


class peeringdb_asn(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = pdb_models.Network.objects.filter(status="ok")
        if self.q:
            try:
                int(self.q)
                qs = qs.filter(asn__istartswith=self.q)
            except ValueError:
                qs = qs.filter(name__istartswith=self.q)

        if not qs.count():
            return [pdb_models.Network(asn=self.q, name="Unknown ASN")]

        return qs

    def get_result_label(self, item):
        return f"AS{item.asn} {item.name}"

    def get_result_value(self, item):
        return item.asn


class peeringdb_org(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        qs = pdb_models.Organization.objects.filter(status="ok")
        if self.q:
            qs = qs.filter(name__istartswith=self.q)
        return qs
