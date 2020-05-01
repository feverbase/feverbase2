import sys

sys.path.append('./fetch')
from faucets import clinicaltrialsgov
from faucets import eu
from faucets import isrctn
from . import utils

sys.path.append('../')
from utils import db, ms, location

from search import mongo_to_meili

TERMS = utils.get_query_terms()

########################################################
### UPDATE TRANSLATE FUNCTION WHEN ADDING NEW SOURCE ###
########################################################

def get_records():
    data = {}
    for query in TERMS:
        # try:
        #     print(f"Crawling {chictr.SOURCE}...")
        #     data.update(chictr.find(query))
        # except Exception as e:
        #     print(e)

        try:
            print(f"Crawling {clinicaltrialsgov.SOURCE}...")
            data.update(clinicaltrialsgov.find(query))
        except Exception as e:
            print(e)

        try:
            print(f"Crawling {eu.SOURCE}...")
            data.update(eu.find(query))
        except Exception as e:
            print(e)

        try:
            print(f"Crawling {isrctn.SOURCE}...")
            data.update(isrctn.find(query))
        except Exception as e:
            print(e)

    articles = [translate(i) for i in data.values()]

    articles_with_location = location.add_location_data(articles)
    
    db.create(articles_with_location)

    # delete location_data key for every article,
    # because it isn't JSON-serializable
    for article in articles:
        article.pop("location_data", None)

    # re-index the meilisearch index
    #mongo_to_meili()
    return articles


def translate(info):
    source = info["_source"]
    # if source == chictr.SOURCE:
    #     return chictr.translate(info)
    if source == clinicaltrialsgov.SOURCE:
        return clinicaltrialsgov.translate(info)
    elif source == eu.SOURCE:
        return eu.translate(info)
    elif source == isrctn.SOURCE:
        return isrctn.translate(info)
    return info
