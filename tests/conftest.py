import sys
import os
import pytest

# before import from serve because need to change db config before it loads
os.environ["PYTESTING"] = "1"

sys.path.append("./")
from serve import app


@pytest.fixture
def client():
    return app.test_client()
