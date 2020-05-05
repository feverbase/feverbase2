import sys

sys.path.append("./fetch")
# from faucets import chictr
from faucets import clinicaltrialsgov
from faucets import eu
from faucets import isrctn
from . import utils

sys.path.append("../")
from utils import db, ms, location

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

    articles = list(map(translate, data.values()))
    articles_with_location = location.add_location_data(articles)

    db.create(db.Article, articles_with_location)

    mongo_to_meili()


def translate(info):
    source = info.get("_source")
    faucet = DRIPPING_FAUCETS.get(source)
    if faucet:
        return faucet.translate(info)
    return info

def preload_filters():
    articles = db.Article.objects()
