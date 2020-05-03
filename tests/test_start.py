import sys
import pytest

from serve import app


@pytest.fixture
def client():
    return app.test_client()


def test_start(client):
    response = client.get("/")
    assert response.status_code == 200
