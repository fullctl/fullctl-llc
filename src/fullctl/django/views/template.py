import os

from django.http import HttpResponse
from django.views import View


class TemplateFileView(View):
    TemplateModel = None

    def get(self, request, template_type):
        # check that template_type exists as a choice
        # in the TemplateModel type field

        type_choices = [
            choice[0] for choice in self.TemplateModel._meta.get_field("type").choices
        ]

        if template_type not in type_choices:
            return HttpResponse(status=404)

        try:
            tmpl = self.TemplateModel(type=template_type)
            path = os.path.join(tmpl.template_loader_paths[0], tmpl.template_path)
            with open(path) as fh:
                template_text = fh.read()
        except KeyError:
            return HttpResponse(status=404)

        # set content type to text/plain and return HttpResponse

        return HttpResponse(template_text, content_type="text/plain")
