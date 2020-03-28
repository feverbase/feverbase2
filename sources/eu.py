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
                    for link in links:
                        country = link.text
                        link = link.get("href")
                        if link:
                            url = f"{BASE_URL}{link}"
                            data[url] = {
                                "SOURCE": SOURCE,
                                "url": url,
                                "title": title,
                                "country": country,
                                "timestamp": date,
                            }

                            count += 1
                print(f"Page {page_num + 1} out of {num_pages} fetched for {query}")

    print(f"Fetched {count} results for {query}")

    return data


def translate(info):
    return info
