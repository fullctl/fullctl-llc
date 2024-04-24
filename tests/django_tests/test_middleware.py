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

    @override_settings(USE_LOCAL_PERMISSIONS=False)
    def test_autocomplete_path(self):
        request = self.rf.get("/autocomplete/", HTTP_AUTHORIZATION="Bearer test")

        # assert attribute error and message
        with self.assertRaises(AttributeError) as e:
            AutocompleteRequestPermsMiddleware(get_response_empty).process_view(
                request, dummy_view, (), {}
            )
        # check if e contains the expected message
        self.assertIn(
            "module 'django.conf.global_settings' has no attribute 'GRAINY_REMOTE'",
            str(e.exception),
        )
