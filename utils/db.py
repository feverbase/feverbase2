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
import datetime

from mongoengine import (
    connect,
    BooleanField,
    DateTimeField,
    DecimalField,
    Document,
    EmailField,
    EmbeddedDocument,
    EmbeddedDocumentField,
    ReferenceField,
    ListField,
    StringField,
    URLField,
    IntField,
    ObjectIdField,
)
from mongoengine_mate import ExtendedDocument

from . import config

# try each env var in order
if config.MONGODB_URI:
  connect(host=config.MONGODB_URI)
else:
  raise Exception("No MongoDB URI specified.")


class Location(ExtendedDocument):
  institution = StringField()
  address = StringField()
  latitude = DecimalField()
  longitude = DecimalField()


class Identity(EmbeddedDocument):
  name = StringField()
  phone = StringField()
  email = EmailField()
  address = StringField()


class Article(ExtendedDocument):
  # primary fields
  title = StringField()
  url = URLField(unique=True)
  timestamp = DateTimeField()

  # additional fields
  overall_status = StringField()
  recruiting_status = StringField()
  sex = ListField(StringField(), default=["male", "female"])
  target_disease = StringField()
  intervention = StringField()
  sponsor = StringField()
  summary = StringField()
  location = StringField()
  location_data = ReferenceField(Location)
  institution = StringField()
  contact = EmbeddedDocumentField(Identity)

  location_data = ObjectIdField()

  # optional fields
  sample_size = IntField()
  abandoned = BooleanField()
  abandoned_reason = StringField()

  # default sort timestamp descending
  meta = {
      "ordering": ["-timestamp"],
      "strict": False,
  }

  def __str__(self):
    return self.url

  # PATCH: match smart_update by url instead of id
  # https://mongoengine-mate.readthedocs.io/_modules/mongoengine_mate/document.html#ExtendedDocument.smart_update
  @classmethod
  def _smart_update(cls, obj, upsert=False):
    """
    Update one document, locate the document by url, then only update
    the field defined with the ExtendedDocument instance. None field is
    ignored.

    :type obj: ExtendedDocument

    :rtype: int
    :return: 0 or 1, number of document been updated
    """
    if isinstance(obj, cls):
      dct = obj.to_dict(include_none=False)
      url_field_name = cls.url.name
      if url_field_name in dct:
        dct.pop(url_field_name)
      return cls.objects(__raw__={
          "url": obj.url
      }).update_one(upsert=upsert, **dct)
    else:  # pragma: no cover
      raise TypeError


class FilterOption(ExtendedDocument):
  key = StringField()
  value = StringField()

  meta = {
      "indexes": [{
          "fields": ["key", "value"],
          "unique": True
      }],
      "ordering": ["key", "value"],
  }


class Patient(Document):
  email = StringField()
  first_name = StringField()
  last_name = StringField()
  age = IntField()
  sex = StringField()
  symptoms = ListField(StringField())


def create(Model, objects):
  """
  Input: list of objects (dictionaries).
  Output: None

  Posts a list of objects to Mongo collection Model.
  """
  docs = list(map(lambda o: Model(**o), objects))
  Model.smart_update(docs, upsert=True)
