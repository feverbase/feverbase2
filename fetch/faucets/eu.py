# Copyright 2020 The Feverbase Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from bs4 import BeautifulSoup
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import utils
import re
import time
import logging
import os

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

SOURCE = "clinicaltrialsregister.eu"
FILENAME = "eu.json"
BASE_URL = "https://www.clinicaltrialsregister.eu"
QUERY_URL = "{BASE_URL}/ctr-search/search?query={query}&dateFrom=2019-12-01"
PAGINATE_QUERY = "&page={page_num}"

logger = logging.getLogger(__name__)


def find(query, existing):
  data = {}
  count = 0
  url = QUERY_URL.format(BASE_URL=BASE_URL, query=query)
  page = requests.get(url, verify=False)
  if page.status_code == 200:
    soup = BeautifulSoup(page.content, "html.parser")

    links = [link.get("href") for link in soup.findAll("a", href=True)]

    page_links = [int(link.split("=")[1]) for link in links if "&page" in link]

    if page_links == []:
      num_pages = 1
    else:
      num_pages = max(page_links)

    for page_num in range(num_pages):
      url = QUERY_URL.format(
          BASE_URL=BASE_URL,
          query=query) + PAGINATE_QUERY.format(page_num=page_num)
      time.sleep(1)
      page = requests.get(url, verify=False)
      if page.status_code == 200:
        soup = BeautifulSoup(page.content, "html.parser")

        result_tables = soup.findAll("table", {"class": "result"})

        for result in result_tables:
          links = result.findAll("a", href=True)

          spans = result.findAll("span", {"class": "label"})

          next_siblings = [span.next_sibling.strip() for span in spans]

          date = next_siblings[2]
          if "Information" in date:
            date = None
          title = next_siblings[4]

          # looks like some studies are done for multiple countries
          for i in range(len(links)):
            link = links[i]
            country = link.text
            link = link.get("href")

            url = f"{BASE_URL}{link}"

            # skip duplicates
            if url in existing:
              continue
            existing.add(url)

            page = requests.get(url, verify=False)
            if page.status_code == 200:
              soup = BeautifulSoup(page.content, "html.parser")

              try:
                intervention = None
                sponsor = None
                main_objective = None
                secondary_objectives = None
                location = None
                institution = None
                contact_email = None
                contact_street_address = None
                contact_town_city = None
                contact_country = None
                sample_size = None

                td_second = soup.findAll("td", {"class": "second"})
                elems = [a.text.strip() for a in td_second]
                for a in td_second:
                  if (a.text.strip() ==
                      "Medical condition(s) being investigated"):
                    target_disease = a.next_sibling.find("td").text
                  if a.text.strip() == "Female":
                    female = a.next_sibling.text.strip() == "Yes"
                  if a.text.strip() == "Male":
                    male = a.next_sibling.text.strip() == "Yes"
                  if a.text.strip() == "Trade name":
                    intervention = a.next_sibling.text
                  if a.text.strip() == "Product name":
                    intervention = a.next_sibling.text
                  if a.text.strip() == "Name of Sponsor":
                    sponsor = a.next_sibling.text
                  if a.text.strip() == "Main objective of the trial":
                    main_objective = a.next_sibling.find("td").text
                  if (a.text.strip() == "Secondary objectives of the trial"):
                    secondary_objectives = a.next_sibling.find("td").text
                  if a.text.strip() == "Country":
                    location = a.next_sibling.text
                  if a.text.strip() == "Name of organisation":
                    institution = a.next_sibling.text
                  if a.text.strip() == "E-mail":
                    contact_email = a.next_sibling.text
                  if a.text.strip() == "Street Address":
                    contact_street_address = a.next_sibling.text
                  if a.text.strip() == "Town/ city":
                    contact_town_city = a.next_sibling.text
                  if a.text.strip() == "Country":
                    contact_country = a.next_sibling.text

                  # none if 0 or can't parse
                  try:
                    if a.text.strip() in [
                        "In the member state",
                        "In the EEA",
                        "In the whole clinical trial",
                    ]:
                      sample_size = (int(a.next_sibling.text) or None)
                  except:
                    sample_size = None

                sex = []

                if male:
                  sex.append("MALE")
                if female:
                  sex.append("FEMALE")

                contact = {
                    "email":
                    contact_email,
                    "address":
                    f"{contact_street_address}, {contact_town_city}, {contact_country}",
                }

                this_entry = {
                    "_source": SOURCE,
                    "url": url,
                    "title": title,
                    "timestamp": date,
                    "recruiting_status": "",
                    "sex": sex,
                    "target_disease": target_disease,
                    "intervention": intervention,
                    "sponsor": sponsor,
                    "summary": f"{main_objective}\n{secondary_objectives}",
                    "location": location,
                    "institution": institution,
                    "contact": contact,
                    "abandoned": None,
                    "sample_size": sample_size,
                }

                data[url] = this_entry
                count += 1
              except Exception as e:
                logger.error(f"[URL: {url}] {e}")

        logger.info(
            f"Page {page_num + 1} out of {num_pages} fetched for {query}")

  logger.info(f"Fetched {count} results for {query}")

  return data


def translate(info):
  del info["_source"]
  return info
