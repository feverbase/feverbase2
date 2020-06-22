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

logger = logging.getLogger(__name__)


def to_iso8601(date):
    comps = date.split("/")
    if len(comps) == 3:
        return f"{comps[2]}-{comps[1]}-{comps[0]}"
    else:
        return None


def find(query, existing):
    data = {}
    count = 0
    url = API_URL.format(query=query)
    results = requests.get(url).text

    root = ET.fromstring(results)

    for trial in root.iter("trial"):
        this_entry = {"_source": SOURCE}
        main = trial.find("main")
        trial_id = main.find("trial_id").text
        url = main.find("url").text
        try:
            # skip duplicates
            if url in existing:
                continue
            existing.add(url)

            date_registration = main.find("date_registration").text
            title = main.find("public_title").text
            sponsor = main.find("primary_sponsor").text

            # none if 0 or can't parse
            try:
                sample_size = int(main.find("target_size").text) or None
            except:
                sample_size = None

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
                first_name = primary_contact.find("firstname").text
                last_name = primary_contact.find("lastname").text
                phone = primary_contact.find("telephone").text
                email = primary_contact.find("email").text
                city = primary_contact.find("city").text

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
            overall_status = None
            recruiting_status = None
            try:
                if url:
                    scrape_page = requests.get(url)
                    if scrape_page.status_code == 200:
                        soup = BeautifulSoup(scrape_page.content, "html.parser")

                        def get_info_for_section_title(
                            title,
                            title_tag="h3",
                            title_class="Info_section_title",
                            next_tag="p",
                        ):
                            tag = soup.find(
                                title_tag,
                                attrs={"class": title_class},
                                text=re.compile(title),
                            )
                            container_tag = tag.find_next_sibling(next_tag)
                            # container_tag contains `NavigableString`s potentially separated by <br> tags
                            if container_tag:
                                parts = []
                                for e in container_tag.children:
                                    if isinstance(e, NavigableString) and len(e):
                                        # replace all whitespace with single space
                                        parts.append(re.sub(r"\s+", " ", e).strip())
                                if len(parts):
                                    return "\n".join(parts).strip()

                        ### GET INFO
                        intervention = get_info_for_section_title("Intervention")
                        institution = get_info_for_section_title(
                            "Trial participating centre"
                        )

                        status_context = dict(
                            title_tag="dt",
                            title_class="Meta_name u-eta",
                            next_tag="dd",
                        )
                        overall_status = get_info_for_section_title(
                            "Overall trial status", **status_context
                        )
                        recruiting_status = get_info_for_section_title(
                            "Recruitment status", **status_context
                        )
            except Exception as e:
                logger.error(f"[ID: {trial_id}, URL: {url}] {e}")

            this_entry["title"] = title
            this_entry["url"] = url
            this_entry["timestamp"] = to_iso8601(date_registration)
            this_entry["sample_size"] = sample_size
            this_entry["overall_status"] = overall_status
            this_entry["recruiting_status"] = recruiting_status
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
        except Exception as e:
            logger.error(f"[ID: {trial_id}, URL: {url}] {e}")

    print(f"Fetched {count} results for {query}")
    return data


def translate(info):
    del info["_source"]
    return info
