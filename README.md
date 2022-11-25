# Gazetteer GND Mapping

A DNB dump of 321.087 objects in JSON-LD format (662.7 MiB file) takes about 70
minutes to import into to an SQLite. In contrast, a Gazetteer dump of 138.881
objects in JSON format (101.8 MiB file) is imported in less than a minute. The
database requires at least 60 MiB of disk space.

## Requirements

Create a virtual environment and install the requirements:

```
$ python3 -mvenv virtual-env
$ source virtual-env/bin/activate
$ python3 -m pip install -r requirements.txt
```

## Command-Line Arguments

The following command-line arguments are supported:

| Short | Long        | Description                   |
|-------|-------------|-------------------------------|
| `-o`  | `--output`  | Path to SQLite database file. |
| `-d`  | `--dnb`     | Path to DNB JSON-LD file.     |
| `-g`  | `--gaz`     | Path to Gazetteer JSON file.  |
| `-s`  | `--schema`  | Path to SQLite schema file.   |
| `-v`  | `--verbose` | Increase output verbosity.    |
| `-q`  | `--quiet`   | No output except on error.    |

## Data Import

To import DNB data in JSON-LD format into SQLite 3 database `database.sqlite`,
run:

```
$ python3 import.py --output /path/to/database.sqlite --schema schema.sql --dnb dnb.json
```

Alternatively, the JSON data can be imported into an in-memory database
by specifing the database `:memory:`:

```
$ python3 import.py --output ":memory:" --schema schema.sql --dnb dnb.json
```

To import Gazetteer data in JSON format into the same database, run:

```
$ python3 import.py --output /path/to/database.sqlite --schema schema.sql --gaz gaz.json
```

## Querying Data

The data can be queried with the *sqlite3(1)* command-line tool or the graphical
[SQLite Browser](https://sqlitebrowser.org/). For example, the following SQL
query matches location names:

```sqlite
SELECT
    dnb_meta.dnb_id,
    dnb_meta.pref_name,
    gaz_meta.gaz_id,
    gaz_meta.pref_title
FROM
    dnb_meta
INNER JOIN gaz_meta ON gaz_meta.pref_title = dnb_meta.pref_name;
```

## CSV Export
Output the data directly from SQLite to CSV, for example, to `matches.csv`:

```
sqlite> .headers on
sqlite> .mode csv
sqlite> .output matches.csv
sqlite> .separator "|"
sqlite> SELECT
   ...>     dnb_meta.dnb_id      AS 'dnb_id',
   ...>     dnb_meta.owl_gnd     AS 'dnb_owl_gnd',
   ...>     dnb_meta.pref_name   AS 'dnb_name',
   ...>     gaz_ident_gnd.gnd_id AS 'gaz_gnd_id',
   ...>     gaz_meta.pref_title  AS 'gaz_name'
   ...> FROM
   ...>     dnb_meta
   ...> INNER JOIN gaz_ident_gnd ON gaz_ident_gnd.gnd_id = dnb_meta.dnb_id
   ...> INNER JOIN gaz_meta      ON gaz_meta.gaz_id = gaz_ident_gnd.gaz_id;
sqlite> .quit
```

## Licence
This software is released under the the GNU General Public Licence.

See the file COPYING included with this distribution for the terms of this
licence.
