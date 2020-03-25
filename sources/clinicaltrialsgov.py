import feedparser
import os
import utils

FILENAME = 'clinicaltrialsgov.json'
FILEPATH = os.path.join(utils.FOLDER, FILENAME)

POSTED_WITHIN_DAYS = 200  # posted within the last X days

TERMS = utils.get_queries()

data = []

print('Fetching data for last {} days...'.format(POSTED_WITHIN_DAYS))

for term in TERMS:
  url = 'https://clinicaltrials.gov/ct2/results/rss.xml?rcv_d={}&cond={}&count=10000'.format(POSTED_WITHIN_DAYS, term)

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
  print("Fetched results for {}".format(term))

  for entry in feed['entries']:
    identifier = entry['id']
    # skip duplicates
    if any(d['id'] == identifier for d in data):
      break
    title = entry['title']
    link = entry['link']
    summary = entry['summary']
    published = entry['published_parsed']

    entry_dict = {
      'id': identifier,
      'title': title,
      'link': link,
      'date': published,
    }
    data.append(entry_dict)

data = sorted(data, key=lambda d: d['date'], reverse=True)

print('Fetched {} results'.format(len(data)))

# print(data)
utils.save_json(data, FILEPATH)
print('Saved to {}'.format(FILEPATH))
