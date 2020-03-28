import feedparser
import os
import utils
import requests
from dateutil import parser
from datetime import datetime, timezone
from bs4 import BeautifulSoup
import re
import sys

SOURCE = "clinicaltrials.gov"
FILENAME = "clinicaltrialsgov.json"
POSTED_WITHIN_DAYS = (
    datetime.now() - datetime(2019, 11, 19)
).days  # posted November 19, 2019
STATUS_INDICATORS = ["|", "/", "-", "\\"]


def find(term):
    data = {}

    print(f"Fetching data for last {POSTED_WITHIN_DAYS} days...")

    added_ids = set()

    url = f"https://clinicaltrials.gov/ct2/results/rss.xml?rcv_d={POSTED_WITHIN_DAYS}&cond={term}&count=10000"
    get_scrape_url = (
        lambda trialID: f"https://clinicaltrials.gov/ct2/show/record/{trialID}"
    )

    # feed keys:
    # feed
    # entries
    # bozo
    # headers
    # href
    # status
    # encoding
    # version
    # namespaces
    feed = feedparser.parse(url)
    total = len(feed["entries"])
    print(f"Fetched {total} results for {term}. Parsing...")

    for idx, entry in enumerate(feed["entries"]):
        identifier = entry["id"]
        # skip duplicates
        if identifier in added_ids:
            continue
        added_ids.add(identifier)

        url = entry["link"]
        url = url[: url.find("?")]

        scrape_url = get_scrape_url(identifier)
        try:
            scrape_page = requests.get(scrape_url)
            if scrape_page.status_code != 200:
                continue

            soup = BeautifulSoup(scrape_page.content, "html.parser")
            info = {
                "SOURCE": SOURCE,
                "ID": identifier,
                "URL": url,
                "SCRAPE_URL": scrape_url,
            }
            for th in soup.find_all("th", attrs={"class": "tr-rowHeader"}):
                label = th.get_text()
                if not label:
                    continue

                # remove ICMJE
                key = label.replace("ICMJE", "")
                # remove asterisks
                key = key.replace("*", "")
                # remove parentheticals
                key = re.sub(r"\(.*\)", "", key)
                # remove multi-whitespace
                key = re.sub("\s\s+", " ", key)
                # strip
                key = key.strip()

                td = th.find_next_sibling()

                value = td.get_text().strip()
                # if "Not Provided", set None
                if value == "Not Provided":
                    value = None

                info[key] = value

            data[url] = info
            sys.stdout.write(
                f"  {STATUS_INDICATORS[idx % len(STATUS_INDICATORS)]} Parsed {idx + 1} of {total}. {total - idx - 1} left \r"
            )
            sys.stdout.flush()
        except Exception as e:
            print(e)
            continue

    sys.stdout.write("                               \r")
    sys.stdout.flush()
    print(f"Parsed {len(data)} results")

    return data


def translate(info):
    title = info.get("Official Title", info.get("Brief Title", ""))
    url = info.get("URL", "")

    date = parser.parse(
        info.get("First Posted Date", info.get("First Submitted Date", "")),
        tzinfos={"EST": "UTC-5", "EDT": "UTC-4"},
    )
    timestamp = date.strftime("%Y-%m-%d")

    return {
        "title": title,
        "url": url,
        "timestamp": timestamp,
    }
