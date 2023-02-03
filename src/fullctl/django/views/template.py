import os

from django.http import HttpResponse
from django.views import View


class TemplateFileView(View):
    TemplateModel = None

    def get(self, request, template_type):
        try:
            tmpl = self.TemplateModel(type=template_type)
            path = os.path.join(tmpl.template_loader_paths[0], tmpl.template_path)
            with open(path) as fh:
                template_text = fh.read()
        except KeyError:
            return HttpResponse(status=404)
        return HttpResponse(template_text)
