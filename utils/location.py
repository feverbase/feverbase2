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
    print("Beginning to add location data...")
    institutions = [a.get("institution") for a in articles]

    # get locations for given institutions
    locations = get_locations(institutions)

    # add an article's location data, based on its institution
    for article in articles:
        article["location_data"] = None
        institution = article.get("institution")
        if institution:
            location = locations.get(institution)
            if location:
                article["location_data"] = location.id

    return articles


def get_locations(queries):
    """Return a dict of location objects for the given queries.

    Pull every location from MongoDB. Iterate through queries
    (every institution in articles) and see which ones are already
    present in MongoDB (Location collection). For those that are not,
    make a call to Maps API and store result in an array. At the end,
    insert all "new" location_data to Location collection. Then,
    return a dictionary with location institutions mapping to the document.
    """
    all_location_objects = db.Location.objects().only("institution")
    stored_institutions = [i.institution for i in all_location_objects]

    # for every 'new' instution (i.e. not present in stored_institution),
    # geocode using Google Maps API
    new_location_names = [inst for inst in queries if inst not in stored_institutions]
    # remove duplicates
    new_location_names = list(set(new_location_names))
    new_location_data = []

    for i, inst in enumerate(new_location_names):
        this_location_data = geocode_query(inst)
        if this_location_data:
            new_location_data.append(this_location_data)
            print(f"[{i + 1}/{len(new_location_names)}] Geocoded institution {inst}")
        else:
            # geocoding didn't return any results, still add to database
            new_location_data.append(
                {
                    "institution": inst,
                    "address": None,
                    "latitude": None,
                    "longitude": None,
                }
            )
            print(
                f"[{i + 1}/{len(new_location_names)}] Unable to geocode institution {inst}"
            )

    # get existing locations
    locations = db.Location.objects(institution__in=queries).only("id", "institution")
    # add new locations
    if len(new_location_data):
        print("Inserting new locations into database...")
        locations += db.create(db.Location, new_location_data)

    return {l.institution: l for l in locations}


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
