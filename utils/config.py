import os
from dotenv import load_dotenv

load_dotenv()

mongodb_uri = os.environ.get(
    "MONGODB_TEST_URI" if os.environ.get("PYTESTING") else "MONGODB_URI"
)
