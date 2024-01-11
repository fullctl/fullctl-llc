from django.conf import settings
from rest_framework import serializers
from rest_framework.schemas.openapi import AutoSchema
from rest_framework.schemas.openapi import SchemaGenerator as BaseSchemaGenerator
from rest_framework.schemas.openapi import is_list_view


class SchemaGenerator(BaseSchemaGenerator):
    def has_view_permissions(self, path, method, view):
        generate_service_bridge = getattr(
            settings, "API_DOCS_GENERATE_SERVICE_BRIDGE", False
        )

        if "service-bridge" in path and not generate_service_bridge:
            return False

        return super().has_view_permissions(path, method, view)


class BaseSchema(AutoSchema):

    """
    Augments the openapi schema generation for
    the fullctl API docs
    """

    @property
    def field_instance(self):
        return {"type": "integer", "description": "Organization workspace instance id"}

    def map_field(self, field):
        if hasattr(self, f"field_{field.field_name}"):
            return getattr(self, f"field_{field.field_name}")
        return super().map_field(field)

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

    def get_operation_id(self, path, method):
        """
        We override this so operation ids become "{op} {reftag}"
        """

        # serializer, model = self.get_classes(path, method)
        # op_type = self.get_operation_type(path, method)
        method_name = getattr(self.view, "action", method.lower())

        if is_list_view(path, method, self.view):
            action = "list"
        elif method_name not in self.method_mapping:
            action = method_name
        else:
            action = self.method_mapping[method.lower()]

        # name = self.get_operation_id_base(path, method, action)

        name = self.view.__class__.__name__

        if "service-bridge" in path:
            name = f"Service Bridge: {name}"

        return f"{name} {action}"

    def get_classes(self, *op_args):
        """
        Try to relate a serializer and model class to the openapi operation

        Returns:

        - tuple(serializers.Serializer, models.Model)
        """

        serializer = self.get_serializer(*op_args)
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

        if not model or not hasattr(model, "HandleRef"):
            return op_dict

        # if we were able to get a model we want to include the markdown documentation
        # for the model type in the openapi description field (docs/api/obj_*.md)

        if model:
            augment = getattr(self, f"augment_{op_type}_{model.HandleRef.tag}", None)
            if augment:
                augment(serializer, model, op_dict)

        return op_dict

    def get_components(self, path, method):
        """
        Return components with their properties from the serializer.
        """

        request_serializer = self.get_request_serializer(path, method)
        response_serializer = self.get_response_serializer(path, method)

        components = {}

        if isinstance(request_serializer, serializers.Serializer):
            component_name = self.get_component_name(request_serializer)
            content = self.map_serializer(request_serializer)
            components.setdefault(component_name, content)

        if isinstance(response_serializer, serializers.Serializer):
            component_name = self.get_component_name(response_serializer)
            content = self.map_serializer(response_serializer)
            components.setdefault(component_name, content)

        return components

    def get_serializer(self, path, method, direction="response"):
        view = self.view

        if hasattr(view, "get_serializer_dynamic"):
            return view.get_serializer_dynamic(path, method, direction)

        return super().get_serializer(path, method)

    def get_response_serializer(self, path, method):
        return self.get_serializer(path, method, "response")

    def get_request_serializer(self, path, method):
        return self.get_serializer(path, method, "request")

    def get_request_body(self, path, method):
        if method not in ("PUT", "PATCH", "POST", "DELETE"):
            return {}

        self.request_media_types = self.map_parsers(path, method)

        serializer = self.get_request_serializer(path, method)

        if not isinstance(serializer, serializers.Serializer):
            item_schema = {}
        else:
            item_schema = self._get_reference(serializer)

        return {
            "content": {ct: {"schema": item_schema} for ct in self.request_media_types}
        }

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

    def get_reference(self, serializer):
        return {"$ref": f"#/components/schemas/{self.get_component_name(serializer)}"}

    def get_responses(self, path, method):
        self.response_media_types = self.map_renderers(path, method)

        serializer = self.get_response_serializer(path, method)

        if not isinstance(serializer, serializers.Serializer):
            item_schema = {}
        else:
            item_schema = self.get_reference(serializer)

        response_schema = {
            "type": "object",
            "properties": {
                "data": {
                    "type": "array",
                    "items": item_schema,
                }
            },
        }

        status_code = "201" if method == "POST" else "200"
        return {
            status_code: {
                "content": {
                    ct: {"schema": response_schema} for ct in self.response_media_types
                },
                # description is a mandatory property,
                # https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.2.md#responseObject
                # TODO: put something meaningful into it
                "description": "",
            }
        }


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
        serializer = self.get_serializer(path, method)
        response_schema = self.map_serializer(serializer)
        status_code = "200"

        return {
            status_code: {
                "content": {
                    ct: {"schema": response_schema} for ct in self.response_media_types
                },
                "description": "",
            }
        }
