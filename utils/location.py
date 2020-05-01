import os
import sys
import json
import re
import requests

from . import db

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

    # determine which institutions are not already in Mongo,
    # and add them
    new_locations = fetch_new_locations(institutions)

    db.insert_locations(new_locations)

    # get all mongo ids so we have a mapping from
    # institution -> location_id, including the
    # new ones we just pushed. note that this includes the
    # locations added in insert_new_locations()
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


def fetch_new_locations(queries):
    """Return a list of locations that are not in Mongo

    Pull every location from MongoDB. Iterate through queries
    (every institution in articles) and see which ones are already
    present in MongoDB (Location collection). For those that are not,
    make a call to Maps API and store result in an array. At the end,
    insert all "new" location_data to Location collection.
    """
    all_location_objects = db.Location.objects()
    stored_institutions = [i.institution for i in all_location_objects]

    # iterate list of institutions. if not present in the list of
    # stored institutions, geocode them and add to array
    new_location_data = []
    for query in queries:
        if query not in stored_institutions:
            this_location_data = geocode_query(query)
            new_location_data.append(this_location_data)

    return new_location_data


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
    queries = ["Gunn High School", "Palo Alto High School", "International school of beijing"]
    insert_new_locations(queries)