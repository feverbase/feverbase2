import os
import json
import time
import pickle
import argparse
import dateutil.parser
from random import shuffle, randrange, uniform
from functools import reduce
import re
from datetime import datetime
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
import html

from utils import db, ms

import nltk

# ensure stopwords are downloaded before importing
nltk.download("stopwords")
nltk.download("punkt")

from nltk.corpus import stopwords
from nltk.stem import PorterStemmer

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

# `"April 1, 2020"` or `April1,2020`
quoted_or_single_word = "\\s*(?:(?:(?:\"|')(.*)(?:\"|'))|(?:([^\\s]*)))"
# { regex: filter_key }
CMDS = {
    f"mindate:{quoted_or_single_word}": "min-timestamp",
    f"maxdate:{quoted_or_single_word}": "max-timestamp",
}

ATTRIBUTES_TO_HIGHLIGHT = [
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
]

stemmer = PorterStemmer()
stops = set(stopwords.words("english"))

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

# returns new query string and set of words to highlight
def preprocess(q):
    ## STEP 1: remove non-alphanumeric characters
    q = "".join(filter(str.isalnum, q))

    ## STEP 2: tokenize
    words = nltk.word_tokenize(q)

    ## STEP 3: stem
    # keep non-stem words for highlighting
    highlight = set(words)
    # only keep unique stems
    words = set(stemmer.stem(w) for w in words)
    highlight.update(words)

    ## STEP 4: remove stop words
    words = [w for w in words if w not in stops]

    # join into single string
    return " ".join(words), highlight


def html_escape(x):
    if type(x) == str:
        return html.escape(x)
    if type(x) == list:
        return [html_escape(y) for y in x]
    if type(x) == dict:
        return {html_escape(k): html_escape(v) for k, v in x.items()}
    return x


def postprocess(papers, highlight):
    pattern = re.compile(f"({'|'.join(highlight)})", flags=re.IGNORECASE)
    for p in papers:
        # convert dict timestamp to int
        if type(p.get("timestamp")) != int:
            p["timestamp"] = p.get("timestamp", {}).get("$date", -1)
        for k, v in p.items():
            # html escape data
            v = html_escape(v)

            # trim summary
            if k == "summary" and v:
                orig = v
                v = v[0:500]
                if len(orig) > 500:
                    v += "..."

            # highlight
            if k in ATTRIBUTES_TO_HIGHLIGHT:
                if type(v) == str:
                    v = pattern.sub(r"<em>\1</em>", v)

            p[k] = v


def is_article(a):
    return type(a) == db.Article


def get_cmd_matches(qraw):
    cmd_matches = {}
    if qraw:
        # detect commands
        for cmd, key in CMDS.items():
            match = re.search(cmd, qraw)
            if match:
                # remove from qraw
                whole_thing = match.group(0)
                qraw = qraw.replace(whole_thing, "")

                match = next(m for m in match.groups() if m)
                cmd_matches[key] = match

    return qraw.strip(), cmd_matches


def filter_papers(page, qraw, dynamic_filters=[]):
    if not qraw:
        qs = []
        for f in dynamic_filters:
            key = f["key"][0]
            op = f["op"][0]
            value = f["value"][0]
            qs.append(eval(f"Q({key}__{op}={value})"))

        advanced_filters = reduce(lambda x, y: x & y, qs) if len(qs) else None

        query_set = db.Article.objects(advanced_filters)
        results = list(query_set.skip((page - 1) * PAGE_SIZE).limit(PAGE_SIZE))
        total_hits = len(query_set)
        query_time = None  # cant find rn
        highlight = []  # none rn
    else:
        q, highlight = preprocess(qraw)

        escape = lambda x: x.replace('"', '\\"')
        advanced_filters = []
        for f in dynamic_filters:
            key = f["key"][1]
            op = f["op"][1]
            value = escape(f["value"][1])
            advanced_filters.append(f'{key} {op} "{value}"')

        advanced_filters = "AND".join(advanced_filters)

        options = {
            "filters": advanced_filters,
            "offset": (page - 1) * PAGE_SIZE,
            "limit": PAGE_SIZE,
        }

        # perform meilisearch query

        results = ms_index.search(q, options)

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
        # EDIT: commented out because default sort by relevancy
        # results = sorted(
        #     results.get("hits"), key=lambda r: r.get("timestamp", -1), reverse=True,
        # )
        results = results.get("hits")
        # get formatted results for highlighting terms
        # results = list(map(lambda r: r.get("_formatted", r), results))
        # EDIT: do this manually because meili doesnt handle stemming (YET!)

    # match longest highlight targets first
    ## sort descending by string length
    highlight = sorted(highlight, key=len, reverse=True)

    if len(results) < PAGE_SIZE:
        page = -1

    return results, page, total_hits, query_time, highlight


# -----------------------------------------------------------------------------
# flask request handling
# -----------------------------------------------------------------------------


def default_context(**kws):
    ans = dict(filter_options={}, filters={}, total_count=db.Article.objects.count())
    ans.update(kws)

    # add cmd filters to advanced filters inputs
    filters = dict(ans.get("filters", {}))
    if filters.get("q"):
        # change filter q string
        filters["q"], cmd_matches = get_cmd_matches(ans["filters"]["q"])
        # copy matches into filters
        filters.update(cmd_matches)
        ans.update({"filters": filters})

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
    "min-timestamp",
    "max-timestamp",
    "min-sample_size",
    "max-sample_size",
]


@app.route("/search", methods=["GET"])
def search():
    ctx = default_context(render_format="search", filters=request.args)
    filters = ctx.get("filters", {})

    if request.headers.get("Content-Type", "") == "application/json":
        page = get_page()

        alerts = []

        # { key, op, value }
        # all 2-tuples, first mongo, second meili
        dynamic_filters = []
        # o = original
        for okey, ovalue in filters.items():
            if okey not in ACCEPTED_DYNAMIC_FILTERS or not ovalue:
                continue

            if okey.startswith("min-"):
                op = ("gte", ">=")
                okey = okey[4:]
            elif okey.startswith("max-"):
                op = ("lte", "<=")
                okey = okey[4:]
            else:
                op = ("icontains", "*=")

            key = (okey, okey)
            value = (ovalue, ovalue)

            if okey == "timestamp":
                try:
                    d = dateutil.parser.parse(ovalue)
                    ts = int(d.timestamp())
                    value = (
                        f"datetime.fromtimestamp({ts})",
                        str(ts),
                    )
                    key = ("timestamp", "parsed_timestamp")
                except:
                    alerts.append(
                        {
                            "type": "error",
                            "message": f"Could not parse date filter '{ovalue}'. Please try another date format (e.g. YYYY-MM-DD)",
                        }
                    )
                    continue
            elif okey == "sample_size":
                try:
                    v = int(ovalue)
                    if v < 0:
                        v = 0
                    v = str(v)
                    value = (v, v)
                except:
                    value = ("0", "0")

            dynamic_filters.append({"key": key, "op": op, "value": value})

        old_page = page
        papers, page, total_hits, query_time, highlight = filter_papers(
            page, filters.get("q", ""), dynamic_filters
        )

        # if returned 0 results on first page, give error
        if old_page == 1 and not len(papers):
            alerts.append(
                {
                    "type": "warning",
                    "message": "Sorry, your search did not return any results. Please try rephrasing your query.",
                }
            )

        stats = f"returned"
        if total_hits:
            stats += f" {total_hits} result{'' if total_hits == 1 else 's'}"
        if query_time or query_time == 0:
            stats += f" in {query_time if query_time else '<1'}ms"

        if len(papers) and is_article(papers[0]):
            papers = list(map(lambda p: json.loads(p.to_json()), papers))

        postprocess(papers, highlight)

        return jsonify(dict(page=page, papers=papers, stats=stats, alerts=alerts))
    else:
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
