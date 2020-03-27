from . import chictr # Chinese Clinical Trial Registry
from . import clinicaltrialsgov # US National Library of Medicine Clinial Trials
from . import eu # EU Clinial Trials Register
from . import isrctn # ISRCTN: primary clinial trial registry recognised by WHO and ICMJE
from . import utils

TERMS = utils.get_query_terms()

def get_records():
    data = {}
    for query in TERMS:
        data.update(chictr.find(query))
        data.update(clinicaltrialsgov.find(query))
        data.update(eu.find(query))
        data.update(isrctn.find(query))

    # sort the data and return it
    items = data.values()
    items = sorted(items, key=lambda d: "" if d["timestamp"] == None else d["timestamp"], reverse=True)
    return items
