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
import re
import requests
import utils
import logging

SOURCE = "chictr.org.cn"
FILENAME = "chictr.json"
BASE_URL = "http://www.chictr.org.cn/"
QUERY_URL = "{BASE_URL}/searchprojen.aspx?officialname=&subjectid=&secondaryid=&applier=&studyleader=&ethicalcommitteesanction=&sponsor=&studyailment=&studyailmentcode=&studytype=0&studystage=0&studydesign=0&minstudyexecutetime=&maxstudyexecutetime=&recruitmentstatus=0&gender=0&agreetosign=&secsponsor=&regno=&regstatus=0&country=&province=&city=&institution=&institutionlevel=&measure=&intercode=&sourceofspends=&createyear=0&isuploadrf=&whetherpublic=&btngo=btn&verifycode=&title={query}"
PAGINATE_QUERY = "&page={page_num}"

logger = logging.getLogger(__name__)


def find(query, existing):
  data = {}
  count = 0
  url = QUERY_URL.format(BASE_URL=BASE_URL, query=query)

  page = requests.get(url)

  if page.status_code == 200:
    soup = BeautifulSoup(page.content, 'html.parser')

    results_number = soup.findAll("label")
    num_pages = 0 if len(results_number) == 0 else int(
        re.findall('[0-9]+', str(results_number[0]))[1])

    for page_num in range(1, num_pages + 1):
      url = QUERY_URL.format(
          BASE_URL=BASE_URL,
          query=query) + PAGINATE_QUERY.format(page_num=page_num)
      try:
        page = requests.get(url)
        if page.status_code == 200:
          soup = BeautifulSoup(page.content, 'html.parser')
          records = soup.findAll("table", {"class": "table_list"})
          for result in records:
            trials = result.find_all('tr', {'class': ''})
            for trial in trials:
              try:
                html_info = trial.find_all('td')

                url_path = html_info[2].find_all('p')[0].find_all('a')[0].get(
                    'href')
                url = '{base}{path}'.format(base=BASE_URL, path=url_path)

                # skip duplicates
                if url in existing:
                  continue
                existing.add(url)

                title = html_info[2].find_all('p')[0].find_all('a')[0].find(
                    text=True)
                affiliation = html_info[2].find_all('p')[1].find(
                    text=True).strip()
                date = '-'.join(html_info[4].find(text=True).strip().split('/'))

                info = {
                    'SOURCE': SOURCE,
                    'url': url,
                    'title': title,
                    'affiliation': affiliation,
                    'timestamp': date
                }

                data[url] = info
                count += 1
              except Exception as e:
                logger.error(f"[URL: {url}] {e}")

            logger.info(
                f'Page {page_num} out of {num_pages} fetched {len(trials)} results for {query}'
            )
      except Exception as e:
        logger.error(f"[Page: {page_num}, URL: {url}] {e}")

  logger.info(f"Fetched {count} results for {query}")

  return data


def translate(info):
  return info
