import sys

sys.path.append("./fetch")
# from faucets import chictr
from faucets import clinicaltrialsgov
from faucets import eu
from faucets import isrctn
from . import utils

sys.path.append("../")
from utils import db, ms

from search import mongo_to_meili

TERMS = utils.get_query_terms()
DRIPPING_FAUCETS = {
    # chictr.SOURCE: chictr,
    clinicaltrialsgov.SOURCE: clinicaltrialsgov,
    eu.SOURCE: eu,
    isrctn.SOURCE: isrctn,
}


def run():
    data = {}
    for query in TERMS:
        for source, faucet in DRIPPING_FAUCETS.items():
            try:
                print(f"Crawling {source}...")
                data.update(faucet.find(query))
            except Exception as e:
                print(e)

    articles = map(translate, data.values())
    db.create(articles)

    # re-index the meilisearch index
    mongo_to_meili()


def translate(info):
    source = info["_source"]
    faucet = DRIPPING_FAUCETS[source]
    if faucet:
        return faucet.translate(info)
    return info
