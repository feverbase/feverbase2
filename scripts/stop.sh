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

# Ctrl+C a few times for good measure
# screen -S flask -X stuff $'\003'
# screen -S flask -X stuff $'\003'
# screen -S flask -X stuff $'\003'

kill $(lsof -ti :80)

# kills all screen sessions with same name
#SESSION_NAME='flask'
#screen -ls "$SESSION_NAME" | (
#  IFS=$(printf '\t');
#  sed "s/^$IFS//" |
#  while read -r name stuff; do
#      screen -S "$name" -X stuff $'\003'
#  done
#)
