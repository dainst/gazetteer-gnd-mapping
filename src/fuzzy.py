#!/usr/bin/env python3

"""
fuzzy.py - fuzzy string matching over DNB & Gazetteer data

Usage:

```
$ python3 fuzzy.py --help
$ python3 fuzzy.py --input database.sqlite --meta
$ python3 fuzzy.py --input database.sqlite --names --threshold 0.9
```
"""

import logging
import sqlite3
import sys

from argparse import ArgumentParser, FileType
from pathlib import Path

logger = logging.getLogger('main')


def db_fuzzy_match_meta(con, threshold=0.8):
    """
    Performs fuzzy meta matching.
    """
    logger.debug('starting fuzzy meta matching, this may take several hours ...')
    cur = con.cursor()
    cur.execute("""
        INSERT INTO fuzzy_meta(
            dnb_meta_id, gaz_meta_id, jarow
        ) SELECT
            dnb_meta.id,
            gaz_meta.id,
            jaro_winkler(translit(dnb_meta.pref_name), translit(gaz_meta.pref_title)) AS jw
        FROM
            dnb_meta
        CROSS JOIN gaz_meta
        WHERE jw >= {:.5f}
    """.format(threshold))
    con.commit()


def db_fuzzy_match_names(con, threshold=0.8):
    """
    Performs fuzzy names matching.
    """
    logger.debug('starting fuzzy names matching, this may take several hours ...')
    cur = con.cursor()
    cur.execute("""
        INSERT INTO fuzzy_name (
            dnb_name_id, gaz_name_id, jarow
        ) SELECT
            dnb_name.id,
            gaz_name.id,
            jaro_winkler(translit(dnb_name.var_name), translit(gaz_name.title)) AS jw
        FROM
            dnb_name
        CROSS JOIN gaz_name
        WHERE jw >= {:.5f}
    """.format(threshold))
    con.commit()


def db_init(con):
    """
    Initialises database connection and deletes stale data.
    """
    db_pragma(con)

    cur = con.cursor()
    cur.execute("DELETE FROM fuzzy_meta")
    cur.execute("DELETE FROM fuzzy_name")
    con.commit()


def db_open(db_path, lib_path):
    """
    Opens database, loads sqlean extension, and returns connection handle.
    """
    con = sqlite3.connect(db_path)

    if not con:
        logger.error('failed to open database "{}"'.format(db_path))
        return

    try:
        con.enable_load_extension(True)
        con.load_extension(lib_path)
    except Exception as ex:
        logger.error('failed to load extension "{}": {}'.format(lib_path, str(ex)))

    return con


def db_pragma(con):
    """
    Executes SQLite PRAGMA statements.
    """
    cur = con.cursor()
    cur.execute("PRAGMA journal_mode = OFF")
    cur.execute("PRAGMA synchronous = 0")
    cur.execute("PRAGMA cache_size = 1000000")
    cur.execute("PRAGMA locking_mode = EXCLUSIVE")
    cur.execute("PRAGMA temp_store = MEMORY")
    con.commit()


def parse_args():
    """
    Reads command-line arguments.
    """
    parser = ArgumentParser(description='Gazetteer and DNB fuzzy matching', exit_on_error=True)

    parser.add_argument('-i', '--input',     help='path to SQLite database file', required=True, type=Path)
    parser.add_argument('-l', '--library',   help='path to sqlean fuzzy extension library', default='./fuzzy')
    parser.add_argument('-m', '--meta',      help='match meta data', action='store_true')
    parser.add_argument('-n', '--names',     help='match name data', action='store_true')
    parser.add_argumnet('-t', '--threshold', help='Jaro-Winkler threshold value (default: 0.8)', default=0.8, type=float)
    parser.add_argument('-v', '--verbose',   help='increase output verbosity', action='store_true')

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

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)


if __name__ == '__main__':
    args = parse_args()
    setup_logger(args.verbose)

    con = db_open(args.input, args.library)
    if not con: sys.exit(1)

    db_init(con)

    if (args.meta):
        logger.info('matching DNB and Gazetteer meta titles ...')
        db_fuzzy_match_meta(con, args.threshold)

    if (args.names):
        logger.info('matching DNB and Gazetteer names ...')
        db_fuzzy_match_names(con, args.threshold)
