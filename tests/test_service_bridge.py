import pytest

from fullctl.service_bridge.client import urljoin


@pytest.mark.parametrize(
    "a,b,c,expected",
    [
        ("http://example.com", "foo", "bar", "http://example.com/foo/bar/"),
        ("http://example.com", "foo/", "/bar", "http://example.com/foo/bar/"),
        (
            "http://example.com",
            "foo/",
            "/bar/test/extra",
            "http://example.com/foo/bar/test/extra/",
        ),
        (
            "http://example.com",
            "foo/",
            "/bar/test//extra",
            "http://example.com/foo/bar/test/extra/",
        ),
        ("http://example.com/", "/foo/", "/bar/", "http://example.com/foo/bar/"),
        ("http://example.com/", "/foo//", "//bar/", "http://example.com/foo/bar/"),
        ("http://test/", "/foo//", "//bar/", "http://test/foo/bar/"),
        ("http://example.com/", "/foo/", "bar//", "http://example.com/foo/bar/"),
        (None, "/foo/", "bar//", "/foo/bar/"),
    ],
)
def test_urljoin(a, b, c, expected):
    """
    Tests that calling urljoin with  a,b and c will match the expected result
    """
    assert urljoin(a, b, c) == expected
