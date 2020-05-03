import sys
import json
import re

sys.path.append("../")
from utils import db, ms


def parse_documents():
    parsed_documents = []
    for doc in db.Article.objects:
        entry_json = json.loads(doc.to_json())

        # these values should be guaranteed by Mongo
        _id = entry_json.get("_id")
        assert _id, "_id not present in Mongo document"
        oid = _id.get("$oid")
        assert oid, "$oid not present in Mongo document"

        # remove _id key so we can feed directly to meili
        del entry_json["_id"]
        entry_json["ms-id"] = oid

        sample_size = entry_json.get("sample_size", 0)
        if sample_size == 0:
            sample_size = -1
        entry_json["sample_size"] = sample_size

        # convert timestamp to epoch
        if doc.timestamp:
            entry_json["parsed_timestamp"] = int(doc.timestamp.timestamp())
        else:
            entry_json["parsed_timestamp"] = -1

        parsed_documents.append(entry_json)
    print(f"Retrieved {len(parsed_documents)} documents from MongoDB")
    return parsed_documents


def push_to_meili(documents):
    client = ms.get_ms_client()
    index = ms.get_ms_trials_index(client)

    # we want to delete all current documents in the index
    delete_id = index.delete_all_documents().get("updateId")
    status = None
    while status != "processed":
        update_status = index.get_update_status(delete_id)
        status = update_status.get("status")
    print("[Meili] Successfully cleared previous documents")

    update_id = index.add_documents(documents).get("updateId")

    # don't return until all documents have been pushed
    status = None
    while status != "processed":
        update_status = index.get_update_status(update_id)
        status = update_status.get("status")
    print("[Meili] Successfully uploaded data to Meilisearch")


def mongo_to_meili():
    docs = parse_documents()
    push_to_meili(docs)


def perform_meili_search(query):
    client = ms.get_ms_client()
    index = ms.get_ms_trials_index(client)
    result = index.search(query)
    return result
