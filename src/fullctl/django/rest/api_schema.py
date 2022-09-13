from rest_framework.schemas.openapi import AutoSchema

from fullctl.django.rest.serializers import ModelSerializer


class BaseSchema(AutoSchema):

    """
    Augments the openapi schema generation for
    the fullctl API docs
    """

    def get_operation_type(self, *args):
        """
        Determine if this is a list retrieval operation
        """

        method = args[1]

        if len(args[0]) > 6 and args[0][-6:] == "/{id}/":
            retrieve = True
        else:
            retrieve = False

        if method == "GET" and not retrieve:
            return "list"
        elif method == "GET":
            return "retrieve"
        elif method == "POST":
            return "create"
        elif method == "PUT":
            return "update"
        elif method == "DELETE":
            return "delete"
        elif method == "PATCH":
            return "patch"

        return method.lower()

    def _get_operation_id(self, path, method):
        """
        We override this so operation ids become "{op} {reftag}"
        """

        serializer, model = self.get_classes(path, method)
        op_type = self.get_operation_type(path, method)

        if model:
            return f"{model.HandleRef.tag}.{op_type}"

        return super()._get_operation_id(path, method)

    def get_classes(self, *op_args):
        """
        Try to relate a serializer and model class to the openapi operation

        Returns:

        - tuple(serializers.Serializer, models.Model)
        """

        serializer = self._get_serializer(*op_args)
        model = None
        if hasattr(serializer, "Meta"):
            if hasattr(serializer.Meta, "model"):
                model = serializer.Meta.model
        return (serializer, model)

    def get_operation(self, *args, **kwargs):

        """
        We override this so we can augment the operation dict
        for an openapi schema operation
        """

        op_dict = super().get_operation(*args, **kwargs)

        op_type = self.get_operation_type(*args)

        # check if we have an augmentation method set for the
        # operation type, if so run it

        augment = getattr(self, f"augment_{op_type}_operation", None)

        if augment:
            augment(op_dict, args)

        # attempt to relate a serializer and a model class to the operation

        serializer, model = self.get_classes(*args)

        #if not model:
        #    return op_dict

        # if we were able to get a model we want to include the markdown documentation
        # for the model type in the openapi description field (docs/api/obj_*.md)

        if hasattr(model, "HandleRef"):
            reftag = model.HandleRef.tag
        else:
            reftag = model.__name__.lower()

        if model:
            augment = getattr(self, f"augment_{op_type}_{model.HandleRef.tag}", None)
            if augment:
                augment(serializer, model, op_dict)

        return op_dict

    def request_body_schema(self, op_dict, content="application/json"):
        """
        Helper function that return the request body schema
        for the specified content type
        """

        return (
            op_dict.get("requestBody", {})
            .get("content", {})
            .get(content, {})
            .get("schema", {})
        )


class PeeringDBImportSchema(AutoSchema):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_operation(self, path, method):
        operation = super().get_operation(path, method)
        operation["responses"] = self._get_responses(path, method)
        return operation

    def _get_operation_id(self, path, method):
        return "ix.import_peeringdb"

    def _get_responses(self, path, method):
        self.response_media_types = self.map_renderers(path, method)
        serializer = ModelSerializer()
        response_schema = self._map_serializer(serializer)
        status_code = "200"

        return {
            status_code: {
                "content": {
                    ct: {"schema": response_schema} for ct in self.response_media_types
                },
                "description": "",
            }
        }
