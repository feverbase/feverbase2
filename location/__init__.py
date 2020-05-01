import os
import sys
import json
import re
import requests

sys.path.append("../")
from utils import db, ms

from dotenv import load_dotenv

load_dotenv()

if os.environ.get("GOOGLE_MAPS_KEY"):
    key = os.environ.get("GOOGLE_MAPS_KEY")
    BASE_URL = f"https://maps.googleapis.com/maps/api/geocode/json?key={key}"


"""
run from fetch/__init__.py, take the entire list of
articles as input, and output the same list with each
article's location data
"""
def add_location_data(articles):
    institutions = [a.get("institution") for a in articles]

    # geocode all locations (this only peforms the
    # operation if the location is not already in the
    # database.)
    new_locations = [l for l in get_locations(institutions) if l]

    # push all these newly-fetched locations to the
    # database
    if len(new_locations) > 0:
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

    return articles

"""
run this first on every article, return a list of
all 'new' locations. to be bulk inserted into mongo
"""
def get_locations(queries):
    location_data = []
    for query in queries:
        # if location is already in the db, skip
        if not location_in_db(query):
            this_location_data = geocode_query(query)
            location_data.append(this_location_data)
    return location_data


def location_in_db(query):
    return len(db.Location.objects(institution=query)) > 0

def get_mongo_ids():
    # get all locations from mongo
    all_locations = db.Location.objects()
    # read into dictionary structure
    mappings = {}
    for location in all_locations:
        mappings[location["institution"]] = location.id
    return mappings

def batch_insert_locations(locations):
    objects = []
    for location in locations:
        obj = db.Location(**location)
        objects.append(obj)
    db.Location.smart_insert(objects)

"""
returns {"address": ..., "latitude": ..., "longitude": .. }
"""
def geocode_query(query):
    url = BASE_URL + f"&address={query}"
    data = requests.get(url).json().get("results")

    if data:
        # always just take the first item for now
        if len(data) > 0:
            result = data[0]
            geometry = result.get("geometry", None)
            if geometry:
                location = geometry.get("location", None)
                if location:
                    lat = location.get("lat")
                    lng = location.get("lng")
            address = result.get("formatted_address", None)

            location_details = {
                "institution": query,
                "address": address,
                "latitude": lat,
                "longitude": lng,
            }

            return location_details

