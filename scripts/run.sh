#!/bin/bash

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

cd /root/app
source venv/bin/activate

until python3 serve.py --prod --port 80; do
  EXIT=$?
  if [ $EXIT -eq 143 ]; then
    echo "Exiting gracefully..."
    break
  fi

  echo "Server crashed with exit code $EXIT, respawning..." >&2
  sleep 1
done
