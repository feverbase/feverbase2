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

    preload_filter_options()
    mongo_to_meili()


def translate(info):
    source = info.get("_source")
    faucet = DRIPPING_FAUCETS.get(source)
    if faucet:
        return faucet.translate(info)
    return info


FILTER_OPTION_KEYS = [
    "sponsor",
    # "location",
    "recruiting_status",
]


def preload_filter_options():
    """
    Aggregate all Articles' existing values for given FILTER_OPTION_KEYS and save them to the FilterOption collection in Mongo, replacing those that already exist.
    """

    filter_options = {key: set() for key in FILTER_OPTION_KEYS}
    # keep track of set of casefolded values to preserve case of the common values
    existing_filter_options = {key: set() for key in FILTER_OPTION_KEYS}

    for article in db.Article.objects().only(*FILTER_OPTION_KEYS):
        for key, s in filter_options.items():
            value = str(eval(f"article.{key}") or "")
            if value and value.casefold() not in existing_filter_options[key]:
                s.add(value)
                existing_filter_options[key].add(value.casefold())

    filter_option_data = []
    for key, values in filter_options.items():
        for value in values:
            filter_option_data.append({"key": key, "value": value})
    # clear collection before adding new values
    db.FilterOption.objects.delete()
    db.create(db.FilterOption, filter_option_data)
