mbta.py
=======

A script for viewing predictions of MBTA buses and subway lines. Currently supports all bus lines and Red, Blue, and Orange subway lines (no Green line).


Usage: `./mbta.py [command] [arguments...]`

Commands:
--------

    l[ist]
List MBTA **bus** stops, and their associated tags. No subway stops.


    s[tops] [route tag]
List the stops on a given bus route, and their associated IDs and tags

    p[red] r[ed]|b[lue]|o[range] [stopname]
    p[red] bus [route] [tag]
    p[red] bus [ID]
Show predictions for future stops. Bus stops are identified by either route tag and stop tag, or by stop ID. Subway stops are identified by substring, e.g., "park" will match "Park St" and "Quincy" will match "Quincy Center" AND "Quincy Adams." Green line is not supported (no feed available). Spaces in stopname are OK.

    f[ave]
List favorites

    f[ave] set [alias] [commands...]
Set alias to commands. See examples below. Spaces in commands are ok

    f[ave] delete [aliases...]
Deletes aliases from faves
File where aliases are stored is configurable in the script
Aliases can be recursive!

    help
A help message


Examples:
---------

+ Search for bus stops on a bus line:

        $ ./mbta.py stops 71
          [bunch of stops]

+ Get bus predictions:

        $ ./mbta.py bus 71 2037
          Stop: Mt Auburn St @ Winsor Ave
          
          Direction: Watertown Square via Mt. Auburn St.
           3 min 
          23 min

+ Get subway predictions:

        $ ./mbta.py pred orange down
          Stop: Downtown Crossing
           Destionation: Sullivan Square
             13 min
             ...

+ Use abbreviated commands:

        $ ./mbta.py p r harv
          Stop: Harvard Square
           Destination: Ashmont
             8 min
            10 min
            ...

+ Use faves:

        $ ./mbta.py f set home r harv
        $ ./mbta.py pred home
          Stop: Harvard Square
           Destination: Ashmont
             8 min
            10 min
            ...

+ Use recursive faves:

        $ ./mbta.py f set home r harv
        $ ./mbta.py f set h home
        $ ./mbta.py p h
          [same as above]
