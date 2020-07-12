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
import urllib.request
from http.cookiejar import CookieJar
import os

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.firefox_binary import FirefoxBinary

CURR_FOLDER = os.path.abspath(os.path.dirname(__file__))

profile = webdriver.FirefoxProfile()
profile.accept_untrusted_certs = True
profile.set_preference('browser.download.folderList', 2)  # custom location
profile.set_preference('browser.download.manager.showWhenStarting', False)
profile.set_preference('browser.download.dir',
                       'pdfs/')  # custom location, folder of this file
profile.set_preference("browser.download.manager.alertOnEXEOpen", False)
profile.set_preference("browser.download.manager.closeWhenDone", False)
profile.set_preference("browser.download.manager.focusWhenStarting", False)
profile.set_preference("browser.helperApps.alwaysAsk.force", False)
profile.set_preference(
    'browser.helperApps.neverAsk.saveToDisk',
    'application/pdf, application/octet-stream, application/x-pdf')
profile.set_preference(
    "browser.helperApps.neverAsk.openFile",
    "application/pdf, application/octet-stream, application/x-pdf")
profile.set_preference("pdfjs.disabled", True)  # disable built-in pdf viewer
profile.set_preference("browser.download.useDownloadDir", True)

options = Options()
options.headless = False

# Windows
if os.name == 'nt':
  geckodriver = os.path.join(CURR_FOLDER, 'geckodriver.exe')
  # binary = FirefoxBinary(binary_path)
  driver = webdriver.Firefox(profile,
                             options=options,
                             executable_path=geckodriver)
else:
  driver = webdriver.Firefox(profile, options=options)

# cj = CookieJar()
# op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
wait = WebDriverWait(driver, 30)


def download_pdf(link):
  session = requests.Session()
  for cookie in driver.get_cookies():
    session.cookies.set(cookie['name'], cookie['value'])
  with session.get(link, stream=True) as r:
    r.raise_for_status()
    filename = os.path.basename(urllib.request.urlparse(link).path)
    with open(filename, 'wb') as f:
      for chunk in r.iter_content(chunk_size=8192):
        if chunk:  # filter out keep-alive new chunks
          f.write(chunk)


dois = ['10.3760/cma.j.issn.0254-6450.2020.02.003']

pdfs = []

for i in range(len(dois)):
  link = dois[i]
  if 'doi.org' not in link:
    dois[i] = "https://doi.org/{}".format(link)

for doi in dois:
  driver.get(doi)

  # html = op.open(doi).read().decode('utf-8')
  # soup = BeautifulSoup(html, features="html.parser")
  # for tag in soup.findAll('a'):
  #   href = tag.get('href')
  #   if href and 'pdf' in href:
  #     pdfs.append(href)

# print(pdfs)

# for pdf in pdfs:
#   data = urlopen(pdf).read()
#   filename = os.path.basename(urllib.request.urlparse(pdf).path)
#   with open(filename, 'wb') as f:
#     f.write(data)

driver.close()
