import os
import sys
import json
import re
import requests

import db

from dotenv import load_dotenv

load_dotenv()

if os.environ.get("GOOGLE_MAPS_KEY"):
    key = os.environ.get("GOOGLE_MAPS_KEY")
    BASE_URL = f"https://maps.googleapis.com/maps/api/geocode/json?key={key}"


def add_location_data(articles):
    """Add location information to every article in a list

    For every article in a list, extract the institution name.
    Every institution name is looked-up in the Mongo database,
    if there is already a name->location mapping for the institution,
    skip it. If there isn't a mapping, make a Google Maps API call.

    Once we have ensured every institution name has a corresponding
    Mongo ID, iterate through articles, looking up each institution
    name locaiton_mappings.

    Return the list of articles
    """
    institutions = [a.get("institution") for a in articles]

    # geocode all locations (this only peforms the
    # operation if the location is not already in the
    # database.)
    new_locations = [l for l in get_new_locations(institutions) if l]

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


def get_new_locations(queries):
    """Return a list of locations that are not in Mongo

    For every institution in queries, check if the
    institution exists in Mongo (with location_in_db).
    
    If it does exist, do nothing.

    If it does not exist, geocode the query with Google
    Maps and then add the returned location data to the
    return list.
    """
    location_data = []
    for query in queries:
        # if location is already in the db, skip
        if not location_in_db(query):
            this_location_data = geocode_query(query)
            location_data.append(this_location_data)
    return location_data


def location_in_db(query):
    """Check if a given institution's location info is stored in Mongo"""
    return len(db.Location.objects(institution=query)) > 0


def get_mongo_ids():
    """Return a mapping of every location name to its Mongo ID

    Every entry in the MongoDB "Location" collection has a location
    data ID. We use these IDs to represent relationships from
    Articles to their corresponding location data.

    This function returns a dictionary with institution names as
    keys, and MongoDB IDs as values.
    """

    # get all locations from mongo
    all_locations = db.Location.objects()
    # read into dictionary structure
    mappings = {}
    for location in all_locations:
        mappings[location["institution"]] = location.id
    return mappings


def batch_insert_locations(locations):
    """Insert an array of location_data dictionaries to Mongo"""
    objects = []
    for location in locations:
        obj = db.Location(**location)
        objects.append(obj)
    db.Location.smart_insert(objects)


def geocode_query(query):
    """Input the name of an institution and geocode with Google Maps API

    Construct appropriate URL for GET request to Google Maps API. Parse
    the resulting JSON for only the latitude, longitude, and address
    of the inputted institution name.
    """
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

if __name__ == "__main__":
    print("HELLO")
