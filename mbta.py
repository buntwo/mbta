#!/usr/bin/python3
#
# Shows mbta bus tracking info
#
# author: Brian Tu
# date: 6/23/13

import sys
import urllib.request
import io, gzip
import xml.etree.ElementTree as ET
import json
import pickle as P

### CUSTOMIZE ME #######################
FAVES_FILE = "/home/brian/utils/mbta/mbta_faves"
########################################


# constants
baseURL_bus = "http://webservices.nextbus.com/service/publicXMLFeed?command={0}&a={1}"
baseURL_sub = "http://developer.mbta.com/lib/rthr/{0}.json"
agency = "mbta"
subway_lines = { "red": "red",
                 "r": "red",
                 "blue": "blue",
                 "b": "blue",
                 "orange": "orange",
                 "o": "orange",
                 }


def main(argv):

    commands = { "list" : list_routes,
                 "l": list_routes,
                 "stops": config,
                 "s": config,
                 "pred": predict,
                 "p": predict,
                 "fave": fave,
                 "f": fave,
                 "help": help,
    }

    try:
        commands[argv[0]](*argv[1:])
    except (KeyError, IndexError) as e:
        help()


### COMMAND FUNCTIONS


def list_routes(*args):
    if len(args) != 0:
        die("too many arguments")
    root = getXML(baseURL_bus.format("routeList", agency))
    print("*" * 10 + " BUS ROUTES " + "*" * 10)
    print()
    print("{0:16}  {1}".format("Route", "Tag"))
    for child in root:
        print("{0:16}  {1}".format(child.attrib["title"], child.attrib["tag"]))


def config(*args):
    if len(args) == 0:
        die("no tag given")
    elif len(args) > 1:
        die("too many arguments")

    tag = args[0]
    root = getXML((baseURL_bus + "&r={2}&terse").format("routeConfig", agency, tag))
    print("Route: {0}, tag: {1}".format(root[0].attrib["title"], root[0].attrib["tag"]))
    print()
    # all data is under <route> tag, which is 1st and only child
    stops = {}
    for child in root[0]:
        if child.tag == "stop":
            attribs = child.attrib
            stops[attribs["tag"]] = BusStop(attribs["lat"],
                                        attribs["lon"],
                                        attribs["stopId"] if "stopId" in attribs else "",
                                        attribs["tag"],
                                        attribs["title"]
                                        )
        elif child.tag == "direction":
            print("{0}: {1}".format(child.attrib["name"], child.attrib["title"]))
            for stop in child:
                aStop = stops[stop.attrib["tag"]]
                print("{0:.<50}, ID: {1:6}, tag: {2}".format(aStop.title, aStop.ID, aStop.tag))
            print()



def predict(*args):
    if len(args) == 0:
        die("not enough arguments")

    if args[0] == "bus":
        show_bus_preds(args)
    elif args[0] in subway_lines:
        show_subway_preds(args)
    else:
        faves = load_faves()
        if args[0] not in faves:
            die("unknown alias {0}".format(args[0]))

        new_args = faves[args[0]].split()
        predict(*new_args)


def fave(*args):
    faves = load_faves()
    if len(args) == 0:
        if len(faves) == 0:
            print("No faves")
        else:
            for alias in faves:
                print("{0:10} -> {1}".format(alias, faves[alias]))
    elif args[0] == "set":
        if len(args) < 3:
            die("not enough arguments")
        alias = args[1]
        to = " ".join([x.lower() for x in args[2:]])
        faves[alias] = to
        save_faves(faves)
        print("{0:10} -> {1}".format(alias, to))
    elif args[0] == "delete":
        if len(args) < 2:
            die("not enough arguments")
        for alias in args[1:]:
            try:
                del faves[alias]
                print("Deleted alias '{0}'".format(alias))
            except KeyError:
                print("No alias '{0}'".format(alias))
        save_faves(faves)
    else:
        die("f set [alias] [command] | f delete [aliases...]")
        


### HELPER FUNCTIONS


def getXML(URL):
    req = urllib.request.Request(URL)
    req.add_header("Accept-encoding", "gzip")
    res = urllib.request.urlopen(req)
    if res.headers.get("Content-Encoding") == "gzip":
        data = res.read()
        stream = io.BytesIO(data)
        root = ET.fromstring(gzip.GzipFile(fileobj=stream).read())
    else:
        root = ET.fromstring(res.read())

    if root[0].tag == "Error":
        if root[0].attrib["shouldRetry"] == "false":
            die("input error")
        else:
            die("server error, try again in 10 sec")

    return root


def getJSON(URL):
    req = urllib.request.Request(URL)
    req.add_header("Accept-encoding", "gzip")
    res = urllib.request.urlopen(req)
    if res.headers.get("Content-Encoding") == "gzip":
        data = res.read()
        stream = io.BytesIO(data)
        root = json.loads(gzip.GzipFile(fileobj=stream).read().decode("utf-8"))
    else:
        root = json.loads(res.read().decode("utf-8"))

    return root


# { stop name -> { destination (direction) -> [ (seconds, notes), ...] } }
def add_to_predictions(preds, dest, title, seconds, notes):
    if title in preds:
        if dest in preds[title]:
            preds[title][dest].append((seconds, notes))
        else:
            preds[title][dest] = [(seconds, notes)]
    else:
        preds[title] = { dest: [(seconds, notes)] }


def show_bus_preds(args):
    if len(args) > 3:
        die("too many arguments")
    elif len(args) == 2: # stop ID
        root = getXML((baseURL_bus + "&stopId={2}").format("predictions", agency, args[1]))
    else: # route tag
        root = getXML((baseURL_bus + "&r={2}&s={3}").format("predictions", agency, args[1], args[2]))

    preds = root[0]
    print("Stop: {0}".format(preds.attrib["stopTitle"]))
    print()
    if "dirTitleBecauseNoPredictions" in preds.attrib:
        print("[No predictions]")
        return
    for child in preds:
        if child.tag == "message":
            print("*" * 60)
            print(child.attrib["text"])
            print("*" * 60)
        elif child.tag == "direction":
            print("Direction: {0:<60}".format(child.attrib["title"]))
            for pred in child:
                if "delayed" in pred.attrib and pred.attrib["delayed"] == "true":
                    delayed = "[DELAYED]"
                else:
                    delayed = ""
                print("{0:>2} min {1}".format(pred.attrib["minutes"], delayed))


def show_subway_preds(args):
    if len(args) < 2:
        die("wrong number of arguments")
    URL = baseURL_sub.format(subway_lines[args[0]])

    predictions = {}
    needle = " ".join([x.lower() for x in args[1:]])
    root = getJSON(URL)
    trips = root["TripList"]["Trips"]
    for trip in trips:
        for pred in trip["Predictions"]:
            if needle in pred["Stop"].lower():
                add_to_predictions(predictions, trip["Destination"], pred["Stop"], pred["Seconds"], trip["Note"] if "Note" in trip else "")

    # print
    if len(predictions) == 0:
        print("No stops found")
    else:
        for stop in predictions:
            print("Stop: {0}".format(stop))
            stopInfo = predictions[stop]
            for dest in stopInfo:
                print(" Destination: {0}".format(dest))
                for tup in sorted(stopInfo[dest], key=lambda tup: tup[0]):
                    print("  {0:>2} min                 {1}".format(tup[0]//60, tup[1].upper()))
            print()


def load_faves():
    try:
        faves_file = open(FAVES_FILE, 'rb')
        faves = P.load(faves_file)
    except IOError:
        faves = {}

    return faves


def save_faves(faves):
    faves_file = open(FAVES_FILE, 'wb')
    P.dump(faves, faves_file)
    faves_file.close()


def help():
    print("""
Usage: ./mbta.py [[command] [arguments...]]

Commands:
 l[ist]                           List MBTA *bus* stops, and their associated tags. No subway stops.

 s[tops] [route tag]              List the stops on a given bus route, and their associated IDs and tags

 p[red] r[ed]|b[lue]|o[range]     [stopname]
 p[red] bus [route] [tag]
 p[red] bus [ID]                  Show predictions for future stops. Bus stops are identified by
                                  either route tag and stop tag, or by stop ID. Subway stops are
                                  identified by substring, e.g., "park" will match "Park St" and
                                  "Quincy" will match "Quincy Center" AND "Quincy Adams."
                                  Green line is not supported (no feed available).
                                  Spaces in stopname are OK.

 f[ave]                           List favorites
 f[ave] set [alias] [commands...] Set alias to commands. See examples below. Spaces in commands are ok
 f[ave] delete [aliases...]       Deletes aliases from faves
                                  File where aliases are stored is configurable in the script
                                  Aliases can be recursive!

 help                             This message


 Examples:

./mbta.py stops 71
    [bunch of stops]

./mbta.py pred orange down
    Stop: Downtown Crossing
    13 min
    ...

./mbta.py p r harv
    Stop: Harvard Square
     8 min
    10 min
    ...

./mbta.py f set home r harv -> ./mbta.py pred home
    Stop: Harvard Square
     8 min
    10 min
    ...

./mbta.py f set home r harv -> ./mbta.py f set h home -> ./mbta.py p h
    [same as above]
    """)
    sys.exit()


def die(msg):
    print("Error: " + msg)
    sys.exit(1)


### CLASSES


class BusStop:
    def __init__(self, lat, lon, ID, tag, title):
        self.lat = lat
        self.lon = lon
        self.ID = ID
        self.tag = tag
        self.title = title


### RUN MEEEE
if __name__ == "__main__":
    main(sys.argv[1:])
