from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from fullctl.django.middleware import AutocompleteRequestPermsMiddleware


def get_response_empty(request):
    return HttpResponse()


def dummy_view(request, *args, **kwargs):
    pass  # This is a dummy view function for testing


class AutocompleteRequestPermsMiddlewareTest(SimpleTestCase):
    rf = RequestFactory()

    def test_non_autocomplete_path(self):
        request = self.rf.get("/path/", HTTP_AUTHORIZATION="Bearer test")
        AutocompleteRequestPermsMiddleware(get_response_empty).process_view(
            request, dummy_view, (), {}
        )

        with self.assertRaises(AttributeError):
            request.api_key
        with self.assertRaises(AttributeError):
            request.perms

    @override_settings(USE_LOCAL_PERMISSIONS=True)
    def test_autocomplete_path(self):
        request = self.rf.get("/autocomplete/", HTTP_AUTHORIZATION="Bearer test")
        AutocompleteRequestPermsMiddleware(get_response_empty).process_view(
            request, dummy_view, (), {}
        )

        assert request.api_key == "test"
        assert request.perms is not None
