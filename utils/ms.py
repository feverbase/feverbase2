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

import os
import meilisearch
import logging

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)


def get_ms_client():
  master_key = os.environ.get("MEILI_KEY", "")
  url = os.environ.get("MEILI_URL")

  if not url:
    raise Exception('No Meilisearch URL specified.')

  return meilisearch.Client(url, master_key)


def get_ms_trials_index(client):
  client = get_ms_client()
  indexes = client.get_indexes()

  # no indexes, create one
  if indexes == []:
    logger.warn("[Meili] No index 'trials', creating...")
    index = client.create_index("trials", {"primaryKey": "ms-id"})
  else:
    # if index exists already
    logger.warn("[Meili] Index 'trials' already exists")
    index = client.get_index("trials")

  return index
