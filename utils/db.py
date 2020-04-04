from mongoengine import (
    connect,
    DateTimeField,
    Document,
    StringField,
    URLField,
)
import os
import datetime
from dotenv import load_dotenv
load_dotenv()


if os.environ.get("MONGODB_URI"):
    connect(host=os.environ.get("MONGODB_URI"))
else:
    raise Exception('No MongoDB URI specified.')


class Article(Document):
    title = StringField()
    url = URLField(unique=True)
    timestamp = DateTimeField()

    def __str__(self):
        return self.url


def create(articles):
    """
    Pushes a list of article objects (dictionaries) to MongoDB.
    Automatically checks for duplicates by URL.
    """
    objects = []
    for a in articles:
        obj = Article(
            title=a['title'],
            url=a['url'],
            timestamp=a['timestamp'],
        )
        objects.append(obj)
    Article.objects.insert(objects)