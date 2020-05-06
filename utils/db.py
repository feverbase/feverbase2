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
if config.mongodb_uri:
    connect(host=config.mongodb_uri)
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
    sample_size = IntField(default=0)
    abandoned = BooleanField()
    abandoned_reason = StringField()

    # default sort timestamp descending
    meta = {
        "ordering": ["-timestamp"],
        "strict": False,
    }

    def __str__(self):
        return self.url


class FilterOption(ExtendedDocument):
    key = StringField()
    value = StringField()

    meta = {
        "indexes": [{"fields": ["key", "value"], "unique": True}],
        "ordering": ["key", "value"],
    }


def create(Model, objects):
    """
    Input: list of objects (dictionaries).
    Output: None

    Posts a list of objects to Mongo collection Model.
    """
    docs = list(map(lambda o: Model(**o), objects))
    Model.smart_insert(docs)
