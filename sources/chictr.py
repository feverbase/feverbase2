from bs4 import BeautifulSoup
import re
import requests
import utils

SOURCE = "chictr.org.cn"
FILENAME = "chictr.json"
BASE_URL = "http://www.chictr.org.cn/"
QUERY_URL = "{BASE_URL}/searchprojen.aspx?officialname=&subjectid=&secondaryid=&applier=&studyleader=&ethicalcommitteesanction=&sponsor=&studyailment=&studyailmentcode=&studytype=0&studystage=0&studydesign=0&minstudyexecutetime=&maxstudyexecutetime=&recruitmentstatus=0&gender=0&agreetosign=&secsponsor=&regno=&regstatus=0&country=&province=&city=&institution=&institutionlevel=&measure=&intercode=&sourceofspends=&createyear=0&isuploadrf=&whetherpublic=&btngo=btn&verifycode=&title={query}"
PAGINATE_QUERY = "&page={page_num}"

def find(query):
    data = {}
    count = 0
    url = QUERY_URL.format(BASE_URL=BASE_URL, query=query)

    page = requests.get(url)

    if page.status_code == 200:
        soup = BeautifulSoup(page.content, 'html.parser')

        results_number = soup.findAll("label")
        num_pages = 0 if len(results_number) == 0 else int(re.findall('[0-9]+', str(results_number[0]))[1])

        for page_num in range(1, num_pages + 1):
            url = QUERY_URL.format(BASE_URL=BASE_URL, query=query) + PAGINATE_QUERY.format(page_num=page_num)
            page = requests.get(url)
            if page.status_code == 200:
                soup = BeautifulSoup(page.content, 'html.parser')
                records = soup.findAll("table", {"class": "table_list"})

                for result in records:
                    trials = result.find_all('tr', {'class': ''})
                    for trial in trials:
                        html_info = trial.find_all('td')

                        title = html_info[2].find_all('p')[0].find_all('a')[0].find(text=True)
                        url_path = html_info[2].find_all('p')[0].find_all('a')[0].get('href')
                        affiliation = html_info[2].find_all('p')[1].find(text=True).strip()
                        date = '-'.join(html_info[4].find(text=True).strip().split('/'))
                        url = '{base}{path}'.format(base=BASE_URL, path=url_path)

                        info = {
                            'SOURCE': SOURCE,
                            'url': url,
                            'title': title,
                            'affiliation': affiliation,
                            'timestamp': date
                        }

                        data[url] = info
                        count += 1

                    print(f'Page {page_num} out of {num_pages} fetched {len(trials)} results for {query}')

    print(f"Fetched {count} results for {query}")

    return data

def translate(info):
    return info
