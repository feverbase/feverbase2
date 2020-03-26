import json
import os

FOLDER = os.path.abspath(os.path.dirname(__file__))


def get_query_terms():
    queries = []
    with open(os.path.join(FOLDER, "queries.txt")) as f:
        queries = f.read().splitlines()
    return queries


def save_json(data, filename):
    filepath = os.path.join(FOLDER, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    return filepath
