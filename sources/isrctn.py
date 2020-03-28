from bs4 import BeautifulSoup
import requests
import utils

SOURCE = "isrctn.com"
FILENAME = "isrctn.json"
BASE_URL = "https://www.isrctn.com"
QUERY_URL = "{BASE_URL}/search?q={query}"
PAGINATE_QUERY = "&page={page_num}&searchType=basic-search"


def find(query):
    data = {}
    count = 0
    url = QUERY_URL.format(BASE_URL=BASE_URL, query=query)
    page = requests.get(url)
    if page.status_code == 200:
        soup = BeautifulSoup(page.content, "html.parser")

        results_number = soup.findAll("span", {"class": "Control_name"})
        if len(results_number) == 0:
            num_pages = 0
        else:
            num_pages = int(results_number[1].text.split("of")[1].strip())

        for page_num in range(num_pages):
            url = QUERY_URL.format(
                BASE_URL=BASE_URL, query=query
            ) + PAGINATE_QUERY.format(page_num=page_num)
            page = requests.get(url)
            if page.status_code == 200:
                soup = BeautifulSoup(page.content, "html.parser")
                my_lis = soup.findAll("li", {"class": "ResultsList_item"})
                for result in my_lis:

                    dds = result.findAll("dd", {"class": "Meta_value"})
                    dd_texts = [dd.text.strip() for dd in dds]
                    date = dd_texts[2]

                    # Put date in ISO 8601
                    comps = date.split("/")
                    date = f"{comps[2]}-{comps[1]}-{comps[0]}"

                    for link in result.find_all("a", href=True):
                        title = link.text.split(":")[1].strip()
                        link = link.get("href").split("?")[0]

                        if link:
                            url = f"{BASE_URL}{link}"
                            data[url] = {
                                "SOURCE": SOURCE,
                                "url": url,
                                "timestamp": date,
                                "title": title,
                            }
                            count += 1
    print(f"Fetched {count} results for {query}")
    return data


def translate(info):
    return info
