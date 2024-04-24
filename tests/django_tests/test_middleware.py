from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from fullctl.django.middleware import AutocompleteRequestPermsMiddleware


def get_response_empty(request):
    return HttpResponse()


class AutocompleteRequestPermsMiddlewareTest(SimpleTestCase):
    rf = RequestFactory()

    def test_non_autocomplete_path(self):
        request = self.rf.get("/path/", HTTP_AUTHORIZATION="Bearer test")
        r = AutocompleteRequestPermsMiddleware(get_response_empty).process_view(
            request
        )
        # asert an attribute error using pytest
        with self.assertRaises(AttributeError):
            r.api_key
        self.assertEqual(r.perms, None)
