"""
Classes and functions to handle service bridge data
and relationship management
"""

import json


class JSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, DataObject):
            return o.__dict__
        return super().default(o)


class DataObject:

    """
    Service bridge base data representation

    Will set attributes from initialization arguments

    Supports lazy relationship loading
    """

    # should set this to origin source of data
    # eg., "ixctl"
    source = "__undefined__"

    # human understandable name of object type
    description = "Object"

    # relationship definitions
    relationships = {}

    @property
    def pk(self):
        return self.id

    @property
    def ref_id(self):
        return f"{self.source}:{self.id}"

    @property
    def json(self):
        return json.dumps(self.__dict__, cls=JSONEncoder)

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            if isinstance(v, dict):
                if k in self.relationships:
                    setattr(self, f"_rel_{k}", True)
                    rel_cls = self.relationships[k]["bridge"].Meta.data_object_cls
                else:
                    rel_cls = DataObject

                setattr(self, k, rel_cls(**v))
            elif v is None and k in self.relationships:
                continue
            else:
                setattr(self, k, v)

    def __getattr__(self, k, **kwargs):
        """
        Override the default __getattr__ handling
        to support lazy relationship loading.
        """
        # see if there is a relationship defined for
        # `k`
        rel = self.relationships.get(k)

        if not rel:
            raise AttributeError(k)

        # relationship definition found
        #
        # build filters from relationship filter specification
        filters = {}
        filter_key, value_key = rel["filter"]
        filters[filter_key] = getattr(self, value_key)

        # retrieve relationship
        rel_obj = rel["bridge"]().first(**filters)

        # set relationship attribute
        setattr(self, k, rel_obj)

        # set relationship flag (we check this via hasattr
        # to prevent reloading of already loaded relationships)
        setattr(self, f"_rel_{k}", True)
        return rel_obj

    def ref_rel_id(self, rel):
        rel_id = getattr(self, rel)
        return f"{self.source}:{rel_id}"


class Relationships:

    """
    Relationship manager class

    Currently this only implements a function to preload
    batch style relationships
    """

    @classmethod
    def preload(cls, name, objects):
        """
        Preload the specified relationship on a set of objects

        Arguments:

        - name (`str`) - relationship name
        - objects (`iter`) - list of DataObject type objects
        """

        filters = {}
        if not objects:
            return

        for obj in objects:
            rel = obj.relationships.get(name)
            if not rel:
                raise AttributeError(f"{name} is not a defined relationship for {obj}")

            if hasattr(obj, f"_rel_{name}"):
                continue

            field, attr_name = rel["filter"]
            filters.setdefault(f"{field}s", []).append(getattr(obj, attr_name))

        if not filters:
            return

        rel_objects = {getattr(o, field): o for o in rel["bridge"]().objects(**filters)}

        for obj in objects:
            setattr(obj, name, rel_objects.get(getattr(obj, attr_name)))
            setattr(obj, f"_rel_{name}", True)
