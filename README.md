# Gazetteer & GND Mapping

A collection of Python scripts to import Gazetteer and GND database dumps into
a common SQLite database, and run fuzzy matching methods on the data sets to
find relations based on lexical similarity. The following programs are provided:

* **import.py** – reads JSON and JSON-LD dumps of Gazetteer and GND databases
  into a SQLite database.
* **fuzzy.py** – uses fuzzy matching to find relations between Gazetteer and
  GND data sets. Requires the *sqlean* extension for SQLite.
* **export.py** – writes matches from database to CSV file.
* **html5.py** – exports data in HTML5 format (experimental).

Patience is required when importing and matching data, as JSON parsing takes
some time and matching runs at < 200,000 operations per second. That means, for
example, that the matching of place names will take at least 46 hours.

The database requires about 1 GiB of free disk space for imported data and
matches.

## Requirements

Create a virtual environment and install the dependencies:

```
$ python3 -m venv virtual-env
$ source virtual-env/bin/activate
$ python3 -m pip install -r requirements.txt
```

Additionally, [sqlean](https://github.com/nalgeon/sqlean) is required. Build the
shared libraries and copy `fuzzy.so` to `src/` in this repository:

```
$ git clone --depth 1 https://github.com/nalgeon/sqlean
$ cd sqlean/
$ make compile-linux
```

## Command-Line Arguments

The following command-line arguments are supported:

### import.py

| Short | Long          | Description                                                             |
|-------|---------------|-------------------------------------------------------------------------|
| `-o`  | `--output`    | Path to SQLite database file.                                           |
| `-d`  | `--dnb`       | Path to DNB JSON-LD file.                                               |
| `-g`  | `--gaz`       | Path to Gazetteer JSON file.                                            |
| `-O`  | `--old`       | Enable import of old authority numbers (DNB only, takes several hours). |
| `-s`  | `--schema`    | Path to SQLite schema file.                                             |
| `-v`  | `--verbose`   | Increase output verbosity.                                              |
| `-q`  | `--quiet`     | No output except on error.                                              |

### fuzzy.py

| Short | Long          | Description                                                             |
|-------|---------------|-------------------------------------------------------------------------|
| `-i`  | `--input`     | Path to SQLite database file.                                           |
| `-l`  | `--library`   | Path to sqlean fuzzy extension library (by default: `./fuzzy`).         |
| `-m`  | `--meta`      | Run meta data matching.                                                 |
| `-n`  | `--names`     | Run name data matching.                                                 |
| `-t`  | `--threshold` | Threshold for Jaro-Winkler matching method (by default: 0.8).          |
| `-v`  | `--verbose`   | Increase output verbosity.                                              |

### export.py

| Short | Long          | Description                                                             |
|-------|---------------|-------------------------------------------------------------------------|
| `-i`  | `--input`     | Path to SQLite database file.                                           |
| `-l`  | `--limit`     | Maximum number of data sets to write (optional).                        |
| `-m`  | `--meta`      | Export meta matches.                                                    |
| `-n`  | `--names`     | Export name matches.                                                    |
| `-o`  | `--output`    | Path of CSV output file.                                                |
| `-t`  | `--threshold` | Jaro-Winkler min. value of matches to export (by default: 0.8).        |

## Data Import

To import DNB data in JSON-LD format from file `dnb.jsonld` into the SQLite 3
database `database.sqlite`, run:

```
$ python3 import.py --output /path/to/database.sqlite --schema schema.sql --dnb dnb.jsonld
```

A DNB dump of 321.087 objects (662.7 MiB file) takes about 90 minutes to import.
To import Gazetteer data in JSON format from file `gaz.json` into the same
database, run:

```
$ python3 import.py --output /path/to/database.sqlite --schema schema.sql --gaz gaz.json
```

A Gazetteer dump of 138.881 objects (101.8 MiB file) is imported in less than
two minutes.

## Fuzzy Matching

Run the fuzzy matching of meta data and names based on Jaro-Winkler distance,
with optional threshold value of the result that has to be reached to be stored
in `database.sqlite`:

```
$ python3 fuzzy.py --input database.sqlite --meta --threshold 0.8
$ python3 fuzzy.py --input database.sqlite --names --threshold 0.8
```

**Existing matches will be deleted!** Matching may take several hours/days, as
more than 8,000,000 meta matches and more than 21,000,000 name matches will be
found for a threshold of `0.8`. Expect the database to grow to at least 1 GiB.

## CSV Export

Output the data directly from SQLite to CSV, for example, to `matches.csv`.
First, open the database in the `sqlite3` command-line utility:

```
$ sqlite3 database.sqlite
```

Set the mode to `csv` and the output to the CSV file to write to. Then, execute
the query to export:

```
sqlite> .headers on
sqlite> .mode csv
sqlite> .output matches.csv
sqlite> .separator "|"
sqlite> SELECT
   ...>     dnb_meta.dnb_id      AS dnb_id,
   ...>     dnb_meta.owl_gnd     AS dnb_owl_gnd,
   ...>     dnb_meta.pref_name   AS dnb_name,
   ...>     gaz_ident_gnd.gnd_id AS gaz_gnd_id,
   ...>     gaz_meta.pref_title  AS gaz_name
   ...> FROM
   ...>     dnb_meta
   ...> INNER JOIN gaz_ident_gnd ON gaz_ident_gnd.gnd_id = dnb_meta.dnb_id
   ...> INNER JOIN gaz_meta      ON gaz_meta.gaz_id = gaz_ident_gnd.gaz_id;
sqlite> .quit
```

The CSV field delimiter should be set to something different than `,`, like `|`
in the example above.

The Python script `export.py` dumps matching data to CSV file. Use command-line
argument `--meta` for meta matches (i.e., only matching preferred titles), or
`--names` for matches of all name variants. Default CSV delimiter is `|`.

To write 1000 meta data matches of Jaro-Winkler distance >= 0.8 to CSV file
`meta.csv`, run:

```
$ python3 export.py --input database.sqlite --output meta.csv --meta --limit 1000
```

You can set an custom threshold value. For a minimum distance of 0.98, run:

```
$ python3 export.py --input database.sqlite --output meta.csv --meta --threshold 0.98
```

To export name matches:

```
$ python3 export.py --input database.sqlite --output names.csv --names
```

Optional arguments `--threshold` and `--limit` are permitted as well.

## Querying Data

The data can be queried through the *sqlite3(1)* command-line tool or the
graphical [SQLite Browser](https://sqlitebrowser.org/). For example, the
following SQL query returns matching location names:

```sql
SELECT
    dnb_meta.dnb_id,
    dnb_meta.pref_name,
    gaz_meta.gaz_id,
    gaz_meta.pref_title
FROM
    dnb_meta
INNER JOIN gaz_meta ON gaz_meta.pref_title = dnb_meta.pref_name;
```

## Licence

This software is released under the the GNU General Public Licence.

See the file COPYING included with this distribution for the terms of this
licence.
