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
    send_from_directory,
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
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

from utils import db, ms

# -----------------------------------------------------------------------------
# various globals
# -----------------------------------------------------------------------------

app = Flask(__name__, static_url_path='')
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


def is_article(a):
    return type(a) == db.Article


def filter_sample_size(data, min_subjects, max_subjects):
    # easy case, user did not specify bounds
    if min_subjects == 0 and max_subjects == 0:
        return
    idxs_to_remove = []
    for i in range(len(data)):
        entry = data[i]
        nums = re.findall(
            r"^\D*(\d+)",
            str(
                (
                    entry.sample_size
                    if is_article(entry)
                    else entry.get("sample_size", "")
                )
                or ""
            ),
        )
        if len(nums) >= 1:
            true_num = int(nums[0])
            if not (
                true_num >= min_subjects
                and (true_num <= max_subjects or max_subjects == 0)
            ):
                idxs_to_remove.append(i)
        else:
            idxs_to_remove.append(i)
    idxs_to_remove.sort(reverse=True)
    for i in idxs_to_remove:
        data.pop(i)


def filter_intervention(data, intervention):
    if not intervention or not intervention.strip():
        return
    intervention = intervention.lower().strip()
    idxs_to_remove = []
    for i in range(len(data)):
        entry = data[i]
        this_intervention = (
            (
                (
                    entry.intervention
                    if is_article(entry)
                    else entry.get("intervention", "")
                )
                or ""
            )
            .lower()
            .strip()
        )
        if intervention not in this_intervention:
            idxs_to_remove.append(i)
    idxs_to_remove.sort(reverse=True)
    for i in idxs_to_remove:
        data.pop(i)


def papers_search(
    page, num_left, qraw, country=None, intervention="", min_subjects=0, max_subjects=0
):
    print(f"papers_search with page={page} num_left={num_left}")
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
        results = list(
            db.Article.objects.skip((page - 1) * PAGE_SIZE).limit(page * PAGE_SIZE)
        )
    else:
        # perform meilisearch query
        results = ms_index.search(qraw, options).get("hits")

    if min_subjects == "" or min_subjects == None:
        min_subjects = 0
    if max_subjects == "" or max_subjects == None:
        max_subjects = 0

    # filter on sample size
    filter_sample_size(results, int(min_subjects), int(max_subjects))

    # filter on intervention type
    filter_intervention(results, intervention)

    if len(results) < num_left:
        new_results, page = papers_search(
            page + 1,
            num_left - len(results),
            qraw,
            country,
            intervention,
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


def default_context(**kws):
    # countries = ["United States", "China"]
    # types = ["Type 1"]  # extract all possible from papers

    ans = dict(
        filter_options={}, filters={},  # dict(countries=countries),  # types=types),
    )
    ans.update(kws)
    ans["adv_filters_in_use"] = any(
        v for k, v in ans.get("filters", {}).items() if k != "q"
    )

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
        ctx = default_context(render_format="recent")
        return render_template("main.html", **ctx)

@app.route("/about")
@limiter.exempt
def about():
    return app.send_static_file('index.html')

@app.route('/assets/<path:path>')
@limiter.exempt
def send_assets(path):
    return send_from_directory('static/assets', path)

@app.route("/filter", methods=["GET"])
def filter():
    filters = request.args  # get the filter requests

    if request.headers.get("Content-Type", "") == "application/json":
        page = get_page()

        results, page = papers_search(
            page,
            PAGE_SIZE,
            filters.get("q", ""),
            filters.get("country", None),
            filters.get("intervention", ""),
            filters.get("min-subjects", None),
            filters.get("max-subjects", None),
        )
        papers = results
        if len(papers) and is_article(papers[0]):
            papers = list(map(lambda p: json.loads(p.to_json()), papers))
        return jsonify(dict(page=page, papers=papers))
    else:
        ctx = default_context(render_format="search", filters=filters)
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
        # init sentry
        sentry_sdk.init(
            dsn="https://22e9a060f25d4a6db5e461e074659a80@o376768.ingest.sentry.io/5197936",
            integrations=[FlaskIntegration()],
        )

        # run on Tornado instead, since running raw Flask in prod is not recommended
        print("starting tornado!")
        from tornado.wsgi import WSGIContainer
        from tornado.httpserver import HTTPServer
        from tornado.ioloop import IOLoop
        from tornado.log import enable_pretty_logging

        try:
            enable_pretty_logging()
            http_server = HTTPServer(WSGIContainer(app))
            http_server.listen(args.port)
            IOLoop.instance().start()
        except KeyboardInterrupt:
            print("Stopping!")
    else:
        print("starting flask!")
        app.debug = False
        try:
            app.run(port=args.port, host="0.0.0.0", debug=True)
        except KeyboardInterrupt:
            print("Stopping!")
