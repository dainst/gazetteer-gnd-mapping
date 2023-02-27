#!/usr/bin/env python3

"""
export.py - export DNB & Gazetteer fuzzy matches to  CSV

Usage:

```
$ python3 export.py --help
$ python3 export.py --input database.sqlite --output meta.csv --meta
$ python3 export.py --input database.sqlite --output names.csv --names --threshold 0.9
```
"""

import csv
import logging
import sqlite3
import sys

from argparse import ArgumentParser, FileType
from pathlib import Path

logger = logging.getLogger('main')


def db_export_fuzzy_meta(con, output, limit=0, threshold=0.8):
    """
    Exports meta data matches to CSV. Uses CSV delimiter "|".
    """
    query = """
        SELECT
            dnb_meta.dnb_id      AS DnbId,
            dnb_meta.pref_name   AS DnbPrefName,
            gaz_ident_gnd.gnd_id AS GazGnd,
            gaz_meta.pref_title  AS GazPrefTitle,
            fuzzy_meta.jarow     AS Threshold
        FROM
            fuzzy_meta
        INNER JOIN dnb_meta      ON dnb_meta.id = fuzzy_meta.dnb_meta_id
        INNER JOIN gaz_meta      ON gaz_meta.id = fuzzy_meta.gaz_meta_id
        INNER JOIN gaz_ident_gnd ON gaz_ident_gnd.gaz_id = gaz_meta.gaz_id
        WHERE Threshold >= {:f}
        GROUP BY dnb_meta.dnb_id
    """.format(threshold)

    if limit > 0: query += " LIMIT {:d}".format(limit)

    cur = con.cursor()
    data = cur.execute(query)

    with open(output, 'w') as f:
        writer = csv.writer(f, delimiter='|')
        writer.writerow(['#DNB ID', 'DNB Pref Name', 'Gaz GND ID', 'Gaz Pref Name', 'Threshold'])
        writer.writerows(data)


def db_export_fuzzy_names(con, output, limit=0, threshold=0.8):
    """
    Exports name matches to CSV. Uses CSV delimiter "|".
    """
    query = """
        SELECT
            dnb_meta.dnb_id      AS DnbId,
            dnb_meta.pref_name   AS DnbPrefName,
            dnb_name.var_name    AS DnbName,
            gaz_ident_gnd.gnd_id AS GazGndId,
            gaz_meta.pref_title  AS GazPrefTitle,
            gaz_name.title       AS GazTitle,
            fuzzy_name.jarow     AS Threshold
        FROM
            fuzzy_name
        INNER JOIN dnb_name      ON dnb_name.id = fuzzy_name.dnb_name_id
        INNER JOIN gaz_name      ON gaz_name.id = fuzzy_name.gaz_name_id
        INNER JOIN dnb_meta      ON dnb_meta.id = dnb_name.dnb_meta_id
        INNER JOIN gaz_meta      ON gaz_meta.gaz_id = gaz_name.gaz_id
        INNER JOIN gaz_ident_gnd ON gaz_ident_gnd.gaz_id = gaz_meta.gaz_id
        WHERE Threshold > {:f}
        GROUP BY dnb_meta.dnb_id
    """.format(threshold)

    if limit > 0: query += " LIMIT {:d}".format(limit)

    cur = con.cursor()
    data = cur.execute(query)

    with open(output, 'w') as f:
        writer = csv.writer(f, delimiter='|')
        writer.writerow(['#DNB ID', 'DNB Pref Name', 'DNB Name', 'Gaz GND ID', \
                         'Gaz Pref Title', 'Gaz Title', 'Threshold'])
        writer.writerows(data)


def db_open(db_path):
    """
    Opens database and returns connection handle.
    """
    con = sqlite3.connect(db_path)
    if not con: logger.error('failed to open database "{}"'.format(db_path))
    return con


def parse_args():
    """
    Reads command-line arguments.
    """
    parser = ArgumentParser(description='DNB & Gazetteer export to CSV', exit_on_error=True)

    parser.add_argument('-i', '--input',     help='path to SQLite database', required=True, type=Path)
    parser.add_argument('-l', '--limit',     help='number of rows to export (optional)', type=int, default=0)
    parser.add_argument('-o', '--output',    help='path of CSV file', required=True)
    parser.add_argument('-t', '--threshold', help='Jaro-Winkler threshold value (default: 0.8)', default=0.8, type=float)
    parser.add_argument('-v', '--verbose',   help='increase output verbosity', action='store_true')

    group = parser.add_mutually_exclusive_group()
    group.add_argument('-m', '--meta',  help='output matched meta data',action='store_true')
    group.add_argument('-n', '--names', help='output matched names', action='store_true')

    args = parser.parse_args()

    return args


def setup_logger(verbose):
    """
    Configures the global logger.
    """
    level = logging.WARNING
    if verbose: level = logging.DEBUG

    logger.setLevel(level)

    ch = logging.StreamHandler()
    ch.setLevel(level)

    formatter = logging.Formatter('%(levelname)s: %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)


if __name__ == '__main__':
    args = parse_args()
    setup_logger(args.verbose)

    con = db_open(args.input)
    if not con: sys.exit(1)

    if (args.meta):
        logger.info('writing meta matches to file {} ...'.format(args.output))
        db_export_fuzzy_meta(con, args.output, args.limit, args.threshold)
    elif (args.names):
        logger.info('writing name matches to file {} ...'.format(args.output))
        db_export_fuzzy_names(con, args.output, args.limit, args.threshold)
    else:
        logger.error('command-line argument --meta or --names required')
