"""
Models to facilitate customization and rendering of jinja2 templates
"""

import os

from django.conf import settings
from django.db import models
from django.utils.html import strip_tags
from jinja2 import DictLoader, Environment, FileSystemLoader

from fullctl.django.exceptions import TemplateRenderError

from .base import HandleRefModel


def make_variable_name(value):
    return f"{value}".replace(" ", "_").replace(".", "_")
    # FIXME: make this work magically, or wait until we are on py3
    # trans = string.maketrans(u" .", u"__")
    # return string.translate(u"{}".format(value), trans)


class TemplateModel(HandleRefModel):
    name = models.CharField(max_length=255)
    body = models.TextField()

    # extended model needs to implement `type` field of type CharField

    class Meta:
        abstract = True

    @property
    def template_path(self):
        """
        Returns the template path using the handleref tag and
        type
        """
        return os.path.join(self.HandleRef.tag, f"{self.type}.txt")

    @property
    def template_loader_paths(self):
        return [
            os.path.join(settings.SERVICE_APP_DIR, "templates", settings.SERVICE_TAG)
        ]

    @property
    def context(self):
        if not hasattr(self, "_context"):
            self._context = {}
        return self._context

    def get_data(self):
        return dict()

    def get_env(self):
        """
        Returns the jinja template environment
        """

        if self.body:
            # if body is not empty, we use a dict loader
            # to make jinja load it as the template
            loader = DictLoader({self.template_path: self.body})
        else:
            # if body is empty we will load the default
            # template from file
            #
            # all templates are located at
            # templates/peerctl/<handle_ref_tag>
            loader = FileSystemLoader(self.template_loader_paths)

        env = Environment(trim_blocks=True, loader=loader, autoescape=True)

        env.filters["make_variable_name"] = make_variable_name

        return env

    def render(self):
        """
        renders a template to UTF-8
        """

        # if content_override is specified return that immediately
        # and skip the template rendering entirely
        if getattr(self, "content_override", None):
            return self.content_override

        env = self.get_env()
        template = env.get_template(self.template_path)
        try:
            return strip_tags(template.render(context=self.context, **self.get_data()))
        except Exception as exc:
            raise TemplateRenderError(exc)
