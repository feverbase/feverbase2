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


class Location(EmbeddedDocument):
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
    recruiting_status = StringField()
    sex = ListField(StringField(), default=["male", "female"])
    target_disease = StringField()
    intervention = StringField()
    sponsor = StringField()
    summary = StringField()
    location = StringField()
    location_data = EmbeddedDocumentField(Location)
    institution = StringField()
    contact = EmbeddedDocumentField(Identity)

    location_data = ObjectIdField()

    # optional fields
    sample_size = IntField(default=0)
    parsed_sample_size = IntField(default=0)
    abandoned = BooleanField()
    abandoned_reason = StringField()

    # default sort timestamp descending
    meta = {
        "ordering": ["-timestamp"],
        "strict": False,
    }

    def __str__(self):
        return self.url


def create(articles):
    """
    Input: list of articles (dictionaries).
    Output: None

    Posts a list of articles to Mongo.
    """
    objects = list(map(lambda a: Article(**a), articles))
    Article.smart_insert(objects)


def insert_locations(locations):
    """
    Input: list of locations (dictionaries).
    Output: None

    Posts a list of locations to Mongo.
    """
    objects = []
    for l in locations:
        obj = Location(**l)
        objects.append(obj)
    Location.smart_insert(objects)
