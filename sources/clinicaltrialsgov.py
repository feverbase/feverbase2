import feedparser
import os
import utils
from dateutil import parser
from datetime import timezone

FILENAME = "clinicaltrialsgov.json"
POSTED_WITHIN_DAYS = 200  # posted within the last X days
TERMS = utils.get_query_terms()

data = []

print(f"Fetching data for last {POSTED_WITHIN_DAYS} days...")

for term in TERMS:
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
        if any(d["id"] == identifier for d in data):
            break
        title = entry["title"]
        url = entry["link"]
        summary = entry["summary"]

        # published = entry['published_parsed']
        # iso = time.strftime('%Y-%m-%dT%H:%M:%S%z', published)
        date = parser.parse(
            entry["published"], tzinfos={"EST": "UTC-5", "EDT": "UTC-4"}
        )  # '%a, %d %b %Y %H:%M:%S %Z'
        iso = date.astimezone(timezone.utc).isoformat()

        entry_dict = {
            "id": identifier,
            "title": title,
            "url": url,
            "date": iso,
        }
        data.append(entry_dict)

data = sorted(data, key=lambda d: d["date"], reverse=True)
# remove id from data
for d in data:
    d.pop("id", None)

print(f"Fetched {len(data)} results")

# print(data)
filepath = utils.save_json(data, FILENAME)
print(f"Saved to {filepath}")
