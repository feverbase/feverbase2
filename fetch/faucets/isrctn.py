import xml.etree.ElementTree as ET
import requests
import utils
import logging
import json
import os
from pprint import pprint
from itertools import groupby
from bs4 import BeautifulSoup, NavigableString
import re

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
        trial_id = main.get("trial_id")
        try:
            date_registration = main.get("date_registration")
            title = main.get("public_title")
            sponsor = main.get("primary_sponsor")
            sample_size = int(main.get("target_size"))
            if sample_size == 0:
                sample_size = None
            url = main.get("url")
            recruitment_status = main.get("recruitment_status")
            sex = trial.find("criteria").get("gender")

            if main.find("hc_freetext") != None:
                target_disease = main.get("hc_freetext")
            else:
                target_disease = None

            if main.find("i_freetext") != None:
                summary = main.get("i_freetext")
                splits = summary.split("\n")
                if len(splits) >= 1:
                    summary = splits[0]
                else:
                    summary = None
            else:
                summary = None

            contacts = trial.find("contacts")
            contacts_list = contacts.findall("contact")

            # filter contacts, if names or country present, assume entry valid
            def has_entries(c):
                return (
                    c.get("firstname", "")
                    + c.get("lastname", "")
                    + c.get("country1", "")
                )

            contacts_list = filter(has_entries, contacts_list)
            # loop by type
            primary_contact = {}
            scientific_contact = {}
            for t, contacts in groupby(contacts_list, key=lambda c: c.find("type")):
                if t == "Public":
                    primary_contact = contacts[0]
                    # just in case no scientific contact, use public one
                    if not scientific_contact:
                        scientific_contact = primary_contact
                elif t == "Scientific":
                    scientific_contact = contacts[0]
                    # just in case no public contact, use scientific one
                    if not primary_contact:
                        primary_contact = scientific_contact

            if primary_contact:
                first_name = primary_contact.get("firstname")
                last_name = primary_contact.get("lastname")
                phone = primary_contact.get("telephone")
                email = primary_contact.get("email")
                city = primary_contact.get("city")

                this_entry["contact"] = {
                    "name": f"{first_name} {last_name}",
                    "phone": phone,
                    "email": email,
                }

            country = None
            countries = trial.find("countries")
            # if only one country, try to use it
            # else, use scientific contact country
            if len(countries) == 1:
                country = countries[0].get("country2")
            if not country:
                country = scientific_contact.get("country1") or primary_contact.get(
                    "country1"
                )

            intervention = None
            institution = None
            try:
                if url:
                    scrape_page = requests.get(url)
                    if scrape_page.status_code == 200:
                        soup = BeautifulSoup(scrape_page.content, "html.parser")

                        def get_info_for_section_title(title):
                            h3 = soup.find(
                                "h3",
                                attrs={"class": "Info_section_title"},
                                text=re.compile(title),
                            )
                            p = h3.find_next_sibling("p")
                            # p contains `NavigableString`s separated by <br> tags
                            if p:
                                parts = []
                                for e in p.children:
                                    if isinstance(e, NavigableString) and len(e):
                                        # replace all whitespace with single space
                                        parts.append(re.sub(r"\s+", " ", e).strip())
                                if len(parts):
                                    return "\n".join(parts).strip()

                        ### GET INFO
                        intervention = get_info_for_section_title("Intervention")
                        institution = get_info_for_section_title("Intervention")
            except Exception as e:
                print(e)

            this_entry["title"] = title
            this_entry["url"] = url
            this_entry["timestamp"] = to_iso8601(date_registration)
            this_entry["sample_size"] = sample_size
            this_entry["recruiting_status"] = recruitment_status
            this_entry["sex"] = sex
            this_entry["target_disease"] = target_disease
            this_entry["intervention"] = intervention
            this_entry["sponsor"] = sponsor
            this_entry["summary"] = summary
            this_entry["institution"] = institution
            this_entry["location"] = country

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
