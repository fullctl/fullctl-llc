import os

from rest_framework import viewsets

from fullctl.django.rest.mixins import CachedObjectMixin, OrgQuerysetMixin


class TemplateRenderView(CachedObjectMixin, OrgQuerysetMixin, viewsets.GenericViewSet):
    def _render(self, request, instance, type, pk, *args, **kwargs):
        model = self.queryset.model

        if pk == "default":
            body = request.data.get("body")

            tmpl = model(name="Default", instance=instance, type=type)

            if not body:
                path = os.path.join(tmpl.template_loader_paths[0], tmpl.template_path)
                with open(path) as fh:
                    body = fh.read()

            tmpl.body = body

            tmpl.full_clean()
        else:
            tmpl = self.queryset.get(id=pk)

        context = kwargs.get("context")
        if context:
            for k, v in context.items():
                tmpl.context[k] = v

        serializer = self.serializer_class(instance=tmpl)
        return serializer
