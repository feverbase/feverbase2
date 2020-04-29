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
    BASE_URL = f"https://mapas.googleapis.com/maps/api/geocode/json?key={key}"


def get_location(query):
    # first look it up in mongo
    mongo_results = db.Location.objects(institution=query)
    if len(mongo_results) > 0:
        res = mongo_results[0]
        location = res["location"]

        return {
            "address": location["address"],
            "latitude": location["latitude"],
            "longitude": location["longitude"],
        }
    # if it doesn't exist in mongo, add it then return
    else:
        url = BASE_URL + f"&address={query}" 
        data = requests.get(url).json().get("results")

        if data:
            # always just take the first item for now
            if len(data) >= 1:
                result = data[0]
                geometry = result.get("geometry", None)
                if geometry:
                    location = geometry.get("location", None)
                    if location:
                        lat = location.get("lat")
                        lng = location.get("lng")
                address = result.get("formatted_address", None)

                location_details = {
                    "address": address,
                    "latitude": lat,
                    "longitude": lng,
                }
                location = {"institution": query, "location": location_details}
                obj = db.Location(**location)
                db.Location.smart_insert([obj])

                location = obj["location"]
                return {
                    "address": location["address"],
                    "latitude": location["latitude"],
                    "longitude": location["longitude"],
                }
