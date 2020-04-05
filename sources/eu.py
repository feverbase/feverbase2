from bs4 import BeautifulSoup
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import utils
import re
import time

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

SOURCE = "clinicaltrialsregister.eu"
FILENAME = "eu.json"
BASE_URL = "https://www.clinicaltrialsregister.eu"
QUERY_URL = "{BASE_URL}/ctr-search/search?query={query}"
PAGINATE_QUERY = "&page={page_num}"


def find(query):
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
                BASE_URL=BASE_URL, query=query
            ) + PAGINATE_QUERY.format(page_num=page_num)
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
                        page = requests.get(url, verify=False)
                        if page.status_code == 200:
                            soup = BeautifulSoup(page.content, "html.parser")

                            sample_size = 0

                            td_second = soup.findAll("td", {"class": "second"})
                            elems = [a.text.strip() for a in td_second]
                            for a in td_second:
                                if (
                                    a.text.strip()
                                    == "Medical condition(s) being investigated"
                                ):
                                    target_disease = a.next_sibling.find("td").text
                                if a.text.strip() == "Female":
                                    female = a.next_sibling.text.strip() == "Yes"
                                if a.text.strip() == "Male":
                                    male = a.next_sibling.text.strip() == "Yes"
                                if a.text.strip() == "Trade name":
                                    intervention = a.next_sibling.text
                                if a.text.strip() == "Name of Sponsor":
                                    sponsor = a.next_sibling.text
                                if a.text.strip() == "Main objective of the trial":
                                    main_objective = a.next_sibling.find("td").text
                                if (
                                    a.text.strip()
                                    == "Secondary objectives of the trial"
                                ):
                                    secondary_objectives = a.next_sibling.find(
                                        "td"
                                    ).text
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
                                if a.text.strip() == "In the member state":
                                    sample_size = int(a.next_sibling.text)
                                if a.text.strip() == "In the EEA":
                                    if sample_size != 0:
                                        try:
                                            sample_size = int(a.next_sibling.text)
                                        except ValueError:
                                            pass
                                if a.text.strip() == "In the whole clinical trial":
                                    if sample_size != 0:
                                        try:
                                            sample_size = int(a.next_sibling.text)
                                        except ValueError:
                                            pass

                            if male and female:
                                sex = "MALE, FEMALE"
                            elif male and not female:
                                sex = "MALE"
                            else:
                                sex = "FEMALE"

                            contact = {
                                "email": contact_email,
                                "address": f"{contact_street_address}, {contact_town_city}, {contact_country}",
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
                                "summary": main_objective + "\n" + secondary_objectives,
                                "location": location,
                                "institution": institution,
                                "contact": contact,
                                "abandoned": None,
                                "sample_size": int(sample_size),
                            }
                            data[url] = this_entry
                            count += 1
                            print(f"Scraped link {i + 1}/{len(links)} for page {page_num + 1}")

                print(f"Page {page_num + 1} out of {num_pages} fetched for {query}")

    print(f"Fetched {count} results for {query}")

    return data


def translate(info):
    return info
