from unittest.mock import patch

import pytest
from django.test.client import Client


def test_health_check(db):
    """
    Use django test client to request `/health` and check if the response
    is ok
    """

    client = Client()
    response = client.get("/health/")
    assert response.status_code == 200
    assert response.content == b""


def test_failing_health_check(db):
    """
    Use django test client to request `/health` and check if the response
    is ok
    """

    client = Client()

    # mock a sideeffect for django.db.connection.cursor
    with patch("django.db.connection.cursor") as mock_cursor:
        mock_cursor.side_effect = Exception("Test exception")
        with pytest.raises(Exception):
            client.get("/health/")
