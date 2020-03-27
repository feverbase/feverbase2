import feedparser
import os
import utils
from dateutil import parser
from datetime import timezone
from bs4 import BeautifulSoup

FILENAME = "clinicaltrialsgov.json"
POSTED_WITHIN_DAYS = 200  # posted within the last X days


def summary_to_dict(summary):
    fields = {}
    soup = BeautifulSoup(summary, "html.parser")
    for b in soup.findAll("b"):
        key = b.get_text()
        # remove colon
        value = b.next_sibling and b.next_sibling[1:].replace("\xa0", " ").strip()
        # if 'recruit' in key.lower() and not value:
        #     value = key
        #     key = 'Stage'
        fields[key] = value
    # last one has value of None, is stage
    if not fields[key]:
        fields["Stage"] = key
        del fields[key]
    return fields


def find(term):
    data = {}

    print(f"Fetching data for last {POSTED_WITHIN_DAYS} days...")

    added_ids = set()

    url = f"https://clinicaltrials.gov/ct2/results/rss.xml?rcv_d={POSTED_WITHIN_DAYS}&cond={term}&count=10000"

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
    print(f"Fetched results for {term}")

    for entry in feed["entries"]:
        identifier = entry["id"]
        # skip duplicates
        if identifier in added_ids:
            continue
        added_ids.add(identifier)

        title = entry["title"]
        url = entry["link"].replace(f"cond={term}&", "")

        # published = entry['published_parsed']
        # iso = time.strftime('%Y-%m-%dT%H:%M:%S%z', published)
        date = parser.parse(
            entry["published"], tzinfos={"EST": "UTC-5", "EDT": "UTC-4"}
        )  # '%a, %d %b %Y %H:%M:%S %Z'
        iso = date.astimezone(timezone.utc).isoformat()

        # fields = summary_to_dict(entry["summary"])

        entry_dict = {
            "title": title,
            "url": url,
            "timestamp": iso,
            # "fields": fields,
        }

        for key, value in summary_to_dict(entry["summary"]).items():
            entry_dict[key] = value

        data[url] = entry_dict

    print(f"Fetched {len(data)} results")

    return data
