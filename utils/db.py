import os
import datetime

from mongoengine import (
    connect,
    DateTimeField,
    Document,
    StringField,
    URLField,
)

from dotenv import load_dotenv

load_dotenv()

if os.environ.get("MONGODB_URI"):
    connect(host=os.environ.get("MONGODB_URI"))
else:
    raise Exception("No MongoDB URI specified.")


class Article(Document):
    title = StringField()
    url = URLField(unique=True)
    timestamp = DateTimeField()

    # default sort timestamp descending
    meta = {"ordering": ["-timestamp"]}

    def __str__(self):
        return self.url


def create(articles):
    """
    Input: list of articles (dictionaries).
    Output: None

    Posts a list of articles to Mongo.
    """
    objects = []
    for a in articles:
        obj = Article(title=a["title"], url=a["url"], timestamp=a["timestamp"],)
        objects.append(obj)
    Article.objects.insert(objects)
