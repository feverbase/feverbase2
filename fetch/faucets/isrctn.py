import xml.etree.ElementTree as ET
import requests
import utils
import logging
import json
import os
from pprint import pprint

SOURCE = "isrctn.com"
FILENAME = "isrctn.json"
API_URL = "http://www.isrctn.com/api/query/format/who?q={query}&dateAssigned%20GT%202019-12-01"
LOG_FILENAME = "logs/isrctn.log"


def setup_logging():
    os.makedirs(os.path.dirname(LOG_FILENAME), exist_ok=True)
    logging.basicConfig(filename=LOG_FILENAME, level=logging.DEBUG)


def to_iso8601(date):
    comps = date.split("/")
    if len(comps) == 3:
        return f"{comps[2]}-{comps[1]}-{comps[0]}"
    else:
        return None


def find(query):
    data = {}
    count = 0
    url = API_URL.format(query=query)
    results = requests.get(url).text

    root = ET.fromstring(results)

    for trial in root.iter("trial"):
        this_entry = {"_source": SOURCE}
        main = trial.find("main")
        trial_id = main.find("trial_id").text
        try:
            date_registration = main.find("date_registration").text
            title = main.find("public_title").text
            sponsor = main.find("primary_sponsor").text
            sample_size = int(main.find("target_size").text)
            if sample_size == 0:
                sample_size = None
            url = main.find("url").text
            recruitment_status = main.find("recruitment_status").text
            sex = trial.find("criteria").find("gender").text

            if main.find("hc_freetext") != None:
                target_disease = main.find("hc_freetext").text
            else:
                target_disease = None

            if main.find("i_freetext") != None:
                summary = main.find("i_freetext").text
                splits = summary.split("\n")
                if len(splits) >= 1:
                    summary = splits[0]
                else:
                    summary = None
            else:
                summary = None

            contacts = trial.find("contacts")
            contacts_list = contacts.findall("contact")
            # 0th is always blank for some reason
            if len(contacts_list) >= 2:
                primary_contact = contacts_list[1]
                first_name = primary_contact.find("firstname").text
                last_name = primary_contact.find("lastname").text
                phone = primary_contact.find("telephone").text
                email = primary_contact.find("email").text
                city = primary_contact.find("city").text
                country = primary_contact.find("country1").text

                this_entry["contact"] = {
                    "name": f"{first_name} {last_name}",
                    "phone": phone,
                    "email": email,
                }

            this_entry["title"] = title
            this_entry["url"] = url
            this_entry["timestamp"] = to_iso8601(date_registration)
            this_entry["sample_size"] = sample_size
            this_entry["recruiting_status"] = recruitment_status
            this_entry["sex"] = sex
            this_entry["target_disease"] = target_disease
            # TODO: Fix this
            this_entry["intervention"] = None
            this_entry["sponsor"] = sponsor
            this_entry["summary"] = summary
            # TODO: Fix this
            this_entry["institution"] = None

            data[url] = this_entry
            count += 1
            # pprint(this_entry)
            logging.info(f"Parsed {url}")
        except Exception as e:
            print(f"Failed on trial id: {trial_id} - {e}")

    print(f"Fetched {count} results for {query}")
    return data


def translate(info):
    del info["_source"]
    return info
