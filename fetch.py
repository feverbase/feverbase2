import os
import time
import pickle
import json
import random
import argparse
import urllib.request

import sources

from utils import Config, safe_pickle_dump

if __name__ == "__main__":

    # parse input arguments
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--results-per-iteration", type=int, default=100, help="passed to arxiv API"
    )
    parser.add_argument(
        "--wait-time",
        type=float,
        default=5.0,
        help="lets be gentle to arxiv API (in number of seconds)",
    )
    parser.add_argument(
        "--break-on-no-added",
        type=int,
        default=1,
        help="break out early if all returned query trials are already in db? 1=yes, 0=no",
    )
    args = parser.parse_args()

    # # lets load the existing database to memory
    # try:
    #     db = pickle.load(open(Config.db_path, 'rb'))
    # except Exception as e:
    #     print('error loading existing database:')
    #     print(e)
    #     print('starting from an empty database')
    #     db = {}

    # # -----------------------------------------------------------------------------
    # # main loop where we fetch the new results
    # print('database has %d entries at start' % (len(db), ))
    # num_added_total = 0

    db = {"data": sources.get_records()}

    print("Saving database with %d trials to %s" % (len(db["data"]), Config.db_path))

    dirname = os.path.dirname(os.path.abspath(__file__))
    with open(f"{dirname}/{Config.db_path}", "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=4)
