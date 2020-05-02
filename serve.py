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
    jsonify,
)
from flask_limiter import Limiter
from werkzeug.security import check_password_hash, generate_password_hash
import pymongo
from mongoengine.queryset.visitor import Q
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from dotenv import load_dotenv
import requests

from utils import db, ms

load_dotenv()

# -----------------------------------------------------------------------------
# various globals
# -----------------------------------------------------------------------------

app = Flask(__name__, static_url_path="")
app.config.from_object(__name__)
limiter = Limiter(app, global_limits=["100 per hour", "20 per minute"])

ms_client = ms.get_ms_client()
ms_index = ms.get_ms_trials_index(ms_client)

slack_api_url = os.environ.get("SLACK_WEBHOOK_URL", "")

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


def filter_papers(
    page, qraw, dynamic_filters={}, min_subjects=0, max_subjects=0,
):
    if min_subjects < 0:
        min_subjects = 0
    if max_subjects < 0:
        max_subjects = 0

    if not qraw:
        qs = [
            eval(f"Q({key}__icontains=value)") for key, value in dynamic_filters.items()
        ]

        # parsed_sample_size is -1 if couldn't parse sample_size, so if filtering
        # on sample_size at all, make sure to exclude the invalid entries by adding >= 0
        if min_subjects or max_subjects:
            qs.append(Q(parsed_sample_size__gte=min_subjects))
        if max_subjects:
            qs.append(Q(parsed_sample_size__lte=max_subjects))

        advanced_filters = reduce(lambda x, y: x & y, qs) if len(qs) else None

        query_set = db.Article.objects(advanced_filters)
        results = list(query_set.skip((page - 1) * PAGE_SIZE).limit(PAGE_SIZE))
        total_hits = len(query_set)
        query_time = None  # cant find rn
    else:
        escape = lambda x: x.replace('"', '\\"')
        advanced_filters = [
            f'{key} *= "{escape(value)}"'
            for key, value in dynamic_filters.items()
            if value
        ]
        # parsed_sample_size is -1 if couldn't parse sample_size, so if filtering
        # on sample_size at all, make sure to exclude the invalid entries by adding >= 0
        if min_subjects or max_subjects:
            advanced_filters.append(f"parsed_sample_size >= {min_subjects}")
        if max_subjects:
            advanced_filters.append(f"parsed_sample_size <= {max_subjects}")

        advanced_filters = "AND".join(advanced_filters)

        options = {
            "filters": advanced_filters,
            "offset": (page - 1) * PAGE_SIZE,
            "limit": PAGE_SIZE,
            "attributesToHighlight": [
                "title",
                "recruiting_status",
                "sex",
                "target_disease",
                "intervention",
                "sponsor",
                "summary",
                "location",
                "institution",
                "contact",
                "abandoned_reason",
            ],
        }

        # perform meilisearch query

        results = ms_index.search(qraw, options)

        # was going to use results.get('exhaustiveNbHits')
        # and prepend 'about' if it is False, but source
        # code of MeiliSearch seems to indicate that it
        # always returns false, so let's just trust this
        # number :)
        # EDIT: nbHits for some reason does not take into account filters, so ignore for now
        # total_hits = results.get("nbHits")
        total_hits = None

        query_time = results.get("processingTimeMs")

        # sort by timestamp descending
        results = sorted(
            results.get("hits"),
            key=lambda r: r.get("timestamp", {}).get("$date", -1),
            reverse=True,
        )

    if len(results) < PAGE_SIZE:
        page = -1

    return results, page, total_hits, query_time


# -----------------------------------------------------------------------------
# flask request handling
# -----------------------------------------------------------------------------


def default_context(**kws):
    ans = dict(filter_options={}, filters={}, total_count=db.Article.objects.count())
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
    # if request.headers.get("Content-Type", "") == "application/json":
    #     page = get_page()

    #     papers = db.Article.objects.skip((page - 1) * PAGE_SIZE).limit(PAGE_SIZE)
    #     return jsonify(
    #         dict(page=page, papers=list(map(lambda p: json.loads(p.to_json()), papers)))
    #     )
    # else:
    ctx = default_context(render_format="recent")
    return render_template("search.html", **ctx)


@app.route("/about")
@limiter.exempt
def about():
    return render_template("about.html")


@app.route("/feedback")
def feedback():
    subject = request.args.get("subject", "")
    body = request.args.get("body", "")
    print(subject, body)
    if not subject or not body:
        return "Please include both subject and body.", 400

    requests.post(slack_api_url, json={"text": f"{subject}:\n{body}"})

    return "Thank you for submitting feedback!"


@app.route("/assets/<path:path>")
@limiter.exempt
def send_assets(path):
    return send_from_directory("static/assets", path)


ACCEPTED_DYNAMIC_FILTERS = [
    "sponsor",
    "target_disease",
    "intervention",
    "location",
    "recruiting_status",
]


@app.route("/search", methods=["GET"])
def search():
    filters = request.args  # get the filter requests

    if request.headers.get("Content-Type", "") == "application/json":
        page = get_page()

        dynamic_filters = {
            key: value
            for key, value in filters.items()
            if key in ACCEPTED_DYNAMIC_FILTERS and type(value) == str and len(value)
        }

        try:
            min_subjects = int(filters.get("min-subjects", 0))
        except:
            min_subjects = 0

        try:
            max_subjects = int(filters.get("max-subjects", 0))
        except:
            max_subjects = 0

        papers, page, total_hits, query_time = filter_papers(
            page, filters.get("q", ""), dynamic_filters, min_subjects, max_subjects,
        )

        stats = f"returned"
        if total_hits:
            stats += f" {total_hits} result{'' if total_hits == 1 else 's'}"
        if query_time:
            stats += f" in {query_time}ms"

        if len(papers) and is_article(papers[0]):
            papers = list(map(lambda p: json.loads(p.to_json()), papers))
        return jsonify(dict(page=page, papers=papers, stats=stats))
    else:
        ctx = default_context(render_format="search", filters=filters)
        return render_template("search.html", **ctx)


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
