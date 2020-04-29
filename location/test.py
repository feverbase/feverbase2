import sys
sys.path.append("../")
from utils import db

from location import get_location

if __name__ == "__main__":
    tests = ["Stanford"]
    for i in tests:
        loc = get_location(i)
        print(loc)
