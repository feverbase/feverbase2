import os
import json
import time
import pickle
import argparse
import dateutil.parser
from random import shuffle, randrange, uniform
from functools import reduce
import re

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
    jsonify,
)
from flask_limiter import Limiter
from werkzeug.security import check_password_hash, generate_password_hash
import pymongo
from mongoengine.queryset.visitor import Q

from utils import db, ms

# -----------------------------------------------------------------------------
# various globals
# -----------------------------------------------------------------------------

app = Flask(__name__)
app.config.from_object(__name__)
limiter = Limiter(app, global_limits=["100 per hour", "20 per minute"])

ms_client = ms.get_ms_client()
ms_index = ms.get_ms_trials_index(ms_client)

PAGE_SIZE = 25

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


def filter_sample_size(data, min_subjects, max_subjects):
    # easy case, user did not specify bounds
    if min_subjects == 0 and max_subjects == 0:
        return data
    return_data = []
    print(min_subjects, max_subjects)
    for entry in data:
        sample_size = str(entry.get("sample_size"))
        nums = re.findall(r"^\D*(\d+)", sample_size)
        if len(nums) >= 1:
            true_num = int(nums[0])
            if true_num >= min_subjects and (
                true_num <= max_subjects or max_subjects == 0
            ):
                return_data.append(entry)
    return return_data


def filter_drug(data, drug):
    drug = drug.lower().strip()
    return_data = []
    for entry in data:
        this_drug = entry.get("intervention", "").lower().strip()
        if drug in this_drug:
            return_data.append(entry)
    return return_data


def papers_search(
    page, num_left, qraw, country=None, drug=None, min_subjects=0, max_subjects=0
):
    # prevent infinite loops when looking for more data
    if (page - 1) * PAGE_SIZE > db.Article.objects.count():
        return [], page

    filterstring = ""
    # right now country is really the only thing we
    # can filter on at the meili level
    if country:
        if " " in country:
            country = f"'{country}'"
        print(country)
        filterstring += f"location={country}"
    options = {
        "filters": filterstring,
        "offset": (page - 1) * PAGE_SIZE,
        "limit": page * PAGE_SIZE,
    }

    if qraw == "":
        papers = db.Article.objects.skip((page - 1) * PAGE_SIZE).limit(page * PAGE_SIZE)
        results = list(map(lambda p: json.loads(p.to_json()), papers))
    else:
        # perform meilisearch query
        results = ms_index.search(qraw, options).get("hits")

    if min_subjects == "" or min_subjects == None:
        min_subjects = 0
    if max_subjects == "" or max_subjects == None:
        max_subjects = 0

    # filter on sample size
    results = filter_sample_size(results, int(min_subjects), int(max_subjects))

    # filter on drug type
    results = filter_drug(results, drug)

    if len(results) < num_left:
        new_results, page = papers_search(
            page + 1,
            num_left - len(results),
            qraw,
            country,
            drug,
            min_subjects,
            max_subjects,
        )
        results.extend(new_results)
        # let frontend no there are no more
        if not len(new_results):
            page = -1

    return results, page


# -----------------------------------------------------------------------------
# flask request handling
# -----------------------------------------------------------------------------


def default_context(papers, **kws):
    papers = list(papers)  # make sure is not QuerySet

    countries = ["United States", "China"]
    # types = ["Type 1"]  # extract all possible from papers

    if len(papers) > 0 and type(papers[0]) == db.Article:
        papers = list(map(lambda p: json.loads(p.to_json()), papers))

    ans = dict(
        # if given a list of Articles, parse as necessary
        # if given a list of dicts, no change necessary
        papers=papers,
        numresults=len(papers),
        totpapers=db.Article.objects.count(),
        filter_options=dict(countries=countries),  # types=types),
        filters={},
    )
    ans.update(kws)
    return ans


def get_page():
    try:
        page = int(request.args.get("page", "1"))
    except:
        page = 1
    if page < 1:
        page = 1
    return page


@app.route("/")
def intmain():
    if request.headers.get("Content-Type", "") == "application/json":
        page = get_page()

        papers = db.Article.objects.skip((page - 1) * PAGE_SIZE).limit(page * PAGE_SIZE)
        return jsonify(
            dict(page=page, papers=list(map(lambda p: json.loads(p.to_json()), papers)))
        )
    else:
        ctx = default_context([], render_format="recent")
        return render_template("main.html", **ctx)


@app.route("/filter", methods=["GET"])
def filter():
    filters = request.args  # get the filter requests

    if request.headers.get("Content-Type", "") == "application/json":
        page = get_page()

        papers, page = papers_search(
            page,
            PAGE_SIZE,
            filters.get("q", ""),
            filters.get("country", None),
            filters.get("drug", None),
            filters.get("min_subjects", None),
            filters.get("max_subjects", None),
        )
        return jsonify(dict(page=page, papers=papers))
    else:
        ctx = default_context([], render_format="search", filters=filters)
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
        app.run(port=args.port, host="0.0.0.0", debug=True)
