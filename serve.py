import os
import json
import time
import pickle
import argparse
import dateutil.parser
from random import shuffle, randrange, uniform
from functools import reduce

from hashlib import md5
from flask import (
    Flask,
    request,
    session,
    url_for,
    redirect,
    render_template,
    abort,
    g,
    flash,
    _app_ctx_stack,
)
from flask_limiter import Limiter
from werkzeug.security import check_password_hash, generate_password_hash
import pymongo
from mongoengine.queryset.visitor import Q

from utils import db
from sources import translate

# -----------------------------------------------------------------------------
# various globals
# -----------------------------------------------------------------------------

app = Flask(__name__)
app.config.from_object(__name__)
limiter = Limiter(app, global_limits=["100 per hour", "20 per minute"])

# -----------------------------------------------------------------------------
# connection handlers
# -----------------------------------------------------------------------------


@app.before_request
def before_request():
    # this will always request database connection, even if we dont end up using it ;\
    g.db = db


@app.after_request
def add_header(r):
    """
    Add headers to both force latest IE rendering engine or Chrome Frame,
    and also to cache the rendered page for 10 minutes.
    """
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    r.headers["Cache-Control"] = "public, max-age=0"
    return r


# -----------------------------------------------------------------------------
# search/sort functionality
# -----------------------------------------------------------------------------


def papers_search(qraw):
    qparts = qraw.lower().strip().split()  # split by spaces
    if not len(qparts):
        papers = db.Article.objects()
    else:
        papers = db.Article.objects(
            reduce(
                lambda a, b: a | b, map(lambda part: Q(title__icontains=part), qparts),
            )
        )
        # papers = list(
        #     filter(lambda d: any(part in d["title"].lower() for part in qparts), db)
        # )
    return papers


# -----------------------------------------------------------------------------
# flask request handling
# -----------------------------------------------------------------------------


def default_context(papers, **kws):
    ans = dict(
        papers=list(map(lambda p: json.loads(p.to_json()), papers)),
        numresults=len(papers),
        totpapers=db.Article.objects.count(),
    )
    ans.update(kws)
    return ans


@app.route("/")
def intmain():
    papers = list(db.Article.objects())
    ctx = default_context(papers, render_format="recent")
    return render_template("main.html", **ctx)


@app.route("/search", methods=["GET"])
def search():
    q = request.args.get("q", "")  # get the search request
    papers = papers_search(q)  # perform the query and get sorted documents
    ctx = default_context(papers, render_format="search")
    return render_template("main.html", **ctx)


# -----------------------------------------------------------------------------
# int main
# -----------------------------------------------------------------------------
if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-p", "--prod", dest="prod", action="store_true", help="run in prod?"
    )
    parser.add_argument(
        "-r",
        "--num_results",
        dest="num_results",
        type=int,
        default=200,
        help="number of results to return per query",
    )
    parser.add_argument(
        "--port", dest="port", type=int, default=5000, help="port to serve on"
    )
    args = parser.parse_args()
    print(args)

    # start
    if args.prod:
        # run on Tornado instead, since running raw Flask in prod is not recommended
        print("starting tornado!")
        from tornado.wsgi import WSGIContainer
        from tornado.httpserver import HTTPServer
        from tornado.ioloop import IOLoop
        from tornado.log import enable_pretty_logging

        enable_pretty_logging()
        http_server = HTTPServer(WSGIContainer(app))
        http_server.listen(args.port)
        IOLoop.instance().start()
    else:
        print("starting flask!")
        app.debug = False
        app.run(port=args.port, host="0.0.0.0")
