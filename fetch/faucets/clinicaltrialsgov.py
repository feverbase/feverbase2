import feedparser
import os
import utils
import requests
from dateutil import parser
from datetime import datetime, timezone
from bs4 import BeautifulSoup
import re
import sys
import logging

SOURCE = "clinicaltrials.gov"
FILENAME = "clinicaltrialsgov.json"
POSTED_WITHIN_DAYS = (
    datetime.now() - datetime(2019, 12, 1)
).days  # posted December 1, 2019
STATUS_INDICATORS = ["|", "/", "-", "\\"]

logger = logging.getLogger(__name__)


def find(term, existing):
    data = {}

    logger.info(f"Fetching data for last {POSTED_WITHIN_DAYS} days...")

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
    logger.info(f"Fetched {total} results for {term}. Parsing...")

    for idx, entry in enumerate(feed["entries"]):
        identifier = entry["id"]

        url = entry["link"]
        url = url[: url.find("?")]

        # skip duplicates
        if url in existing:
            continue
        existing.add(url)

        scrape_url = get_scrape_url(identifier)
        try:
            scrape_page = requests.get(scrape_url)
            if scrape_page.status_code != 200:
                continue

            soup = BeautifulSoup(scrape_page.content, "html.parser")
            info = {
                "_source": SOURCE,
                "_id": identifier,
                "url": url,
                "scrape_url": scrape_url,
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
                # if "Not Provided", set empty string (None causes errors, empty string is fine)
                if value == "Not Provided":
                    value = ""

                info[key] = value

            data[url] = info
            sys.stdout.write(
                f"  {STATUS_INDICATORS[idx % len(STATUS_INDICATORS)]} Parsed {idx + 1} of {total}. {total - idx - 1} left \r"
            )
            sys.stdout.flush()
        except Exception as e:
            logger.error(f"[ID: {identifier}, URL: {url}] {e}")
            continue

    sys.stdout.write("                               \r")
    sys.stdout.flush()
    logger.info(f"Parsed {len(data)} results")

    return data


def translate(info):
    title = info.get("Official Title", info.get("Brief Title", ""))
    url = info.get("url", "")

    date = parser.parse(
        info.get("First Posted Date", info.get("First Submitted Date", "")),
        tzinfos={"EST": "UTC-5", "EDT": "UTC-4"},
    )
    timestamp = date.strftime("%Y-%m-%d")

    recruiting = info.get("Recruitment Status")
    sex = (info.get("Sex/Gender", "")).split("\n")[-1]

    if sex == "":
        sex = None
    elif sex == "All":
        sex = ["male", "female"]
    else:
        sex = [sex.lower()]

    target_disease = (info.get("Condition", "")).split("\n")[0]
    intervention = (info.get("Intervention", "")).split("\n")[0]
    sponsor = info.get("Study Sponsor", "")
    summary = info.get("Detailed Description", info.get("Brief Summary", ""))
    location = info.get("Listed Location Countries", "")
    institution = info.get("Responsible Party", "")
    contacts = {}

    # none if 0 or can't parse
    try:
        sample_size = int(info.get("Estimated Enrollment")) or None
    except:
        sample_size = None

    abandoned = None
    abandoned_reason = None

    d = {
        "title": title,
        "url": url,
        "timestamp": timestamp,
        "recruiting_status": recruiting,
        "sex": sex,
        "target_disease": target_disease,
        "intervention": intervention,
        "sponsor": sponsor,
        "summary": summary,
        "location": location,
        "institution": institution,
        "contact": contacts,
        "sample_size": sample_size,
        "abandoned": abandoned,
        "abandoned_reason": abandoned_reason,
    }

    return d
