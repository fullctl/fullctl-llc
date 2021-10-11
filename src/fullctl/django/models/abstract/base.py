from django.db import models
from django.utils.translation import gettext_lazy as _
from django_handleref.models import HandleRefModel as SoftDeleteHandleRefModel

__all__ = [
    "HandleRefModel",
    "PdbRefModel",
]


class HandleRefModel(SoftDeleteHandleRefModel):
    """
    Like handle ref, but with hard delete
    and extended status types
    """

    status = models.CharField(
        max_length=12,
        default="ok",
        choices=(
            ("ok", _("Ok")),
            ("pending", _("Pending")),
            ("deactivated", _("Deactivated")),
            ("failed", _("Failed")),
            ("expired", _("Expired")),
        ),
    )

    class Meta:
        abstract = True

    def delete(self):
        return super().delete(hard=True)


class PdbRefModel(HandleRefModel):

    """
    Base class for models that reference a peeringdb model
    """

    # id of the peeringdb instance that is referenced by
    # this model
    pdb_id = models.PositiveIntegerField(blank=True, null=True)

    # if object was creates from it's pdb reference, the version
    # at the time of the creation should be stored here
    pdb_version = models.PositiveIntegerField(blank=True, null=True)

    class Meta:
        abstract = True

    class PdbRef:
        pdbctl = None
        fields = {"id": "pdb_id"}

    @classmethod
    def create_from_pdb(cls, pdb_object, save=True, **fields):
        """create object from peeringdb instance"""

        for k, v in cls.PdbRef.fields.items():
            fields[v] = getattr(pdb_object, k, k)

        instance = cls(status="ok", **fields)
        if save:
            instance.save()
        return instance

    @property
    def pdb_ref_tag(self):
        return self.PdbRef.pdbctl.ref_tag

    @property
    def pdb(self):
        """returns PeeringDB object"""
        if not hasattr(self, "_pdb"):
            filters = {}
            for k, v in self.PdbRef.fields.items():
                if v and hasattr(self, v):
                    v = getattr(self, v)
                filters[k] = v

            self._pdb = self.PdbRef.pdbctl().first(**filters)
            if self._pdb is None:
                raise KeyError(
                    f"Cannot find peeringdb reference for {self.pdb_ref_tag}: {filters}"
                )

        return self._pdb
