import sys

sys.path.append('./fetch')
from faucets import clinicaltrialsgov
from faucets import eu
from faucets import isrctn
from . import utils

sys.path.append('../')
from utils import db, ms

from search import mongo_to_meili
from location import get_locations, get_mongo_ids, batch_insert_locations, location_in_db

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

        #try:
        #    print(f"Crawling {eu.SOURCE}...")
        #    data.update(eu.find(query))
        #except Exception as e:
        #    print(e)

        #try:
        #    print(f"Crawling {isrctn.SOURCE}...")
        #    data.update(isrctn.find(query))
        #except Exception as e:
        #    print(e)

    articles = [translate(i) for i in data.values()]
    institutions = [a.get("institution") for a in articles]

    # geocode all locations (this only peforms the
    # operation if the location is not already in the
    # database.)
    new_locations = [l for l in get_locations(institutions) if l]

    # push all these newly-fetched locations to the
    # database
    if new_locations != []:
        batch_insert_locations(new_locations)

    # get all mongo ids so we have a mapping from
    # institution -> location_id, including the
    # new ones we just pushed
    location_mappings = get_mongo_ids()

    # for every article, lookup related institution
    # in our mapping, and add the object_id relating
    # to its location data
    for article in articles:
        institution = article.get("institution", None)
        if institution:
            location_id = location_mappings.get(institution)
            if location_id:
                article["location_data"] = location_id
        else:
            article["location_data"] = None
    
    db.test_create(articles)

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
