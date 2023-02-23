#!/usr/bin/env python3

"""
import.py - Gazetteer & DNB dump to database importer

Usage:

```
$ python3 import.py --help
$ python3 import.py --gaz gaz.json --output database.sqlite --schema schema.sql
$ python3 import.py --dnb dnb.json --output database.sqlite --schema schema.sql
$ python3 import.py --dnb dnb.json --output database.sqlite --schema schema.sql --old
```
"""

import ijson
import logging
import simplejson as json
import sqlite3
import sys

from argparse import ArgumentParser, FileType
from pathlib import Path

logger = logging.getLogger('main')


def db_create_schema(db_path, sql_path):
    """
    Adds SQL schema from file to database.
    """
    logger.debug('Connecting to database "{}" ...'.format(db_path))
    con = sqlite3.connect(db_path)

    logger.debug('Creating database schema from file "{}" ...'.format(sql_path))

    with open(sql_path, 'r') as sql_file:
        cur = con.cursor()
        cur.executescript(sql_file.read())
        con.commit()


def db_import_dnb(con, dnb_id, pref_name, owl_geonames, owl_gnd, owl_loc,
                  owl_viaf, owl_wikidata, var_names=[], old_auths=[]):
    """
    Imports DNB data.
    """
    cur = con.cursor()
    cur.execute("""
        INSERT INTO dnb_meta (
            dnb_id,
            pref_name,
            owl_geonames,
            owl_gnd,
            owl_loc,
            owl_viaf,
            owl_wikidata
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (dnb_id, pref_name, owl_geonames, owl_gnd, owl_loc, owl_viaf, owl_wikidata))
    con.commit()

    if var_names and len(var_names) > 0:
        cur.executemany("""
            INSERT INTO dnb_name (
                dnb_meta_id, var_name
            ) VALUES ((SELECT id FROM dnb_meta WHERE dnb_id = ?), ?)
            """, var_names)
        con.commit()

    if old_auths and len(old_auths) > 0:
        values = []

        for dnb_id, value in old_auths:
            prefix = None
            gnd_id = None

            i = value.find('(')
            j = value.find(')')

            if i == 0 and j > 1:
                prefix = value[i + 1:j]
                gnd_id = value[j + 1:]

            values.append((dnb_id, value, prefix, gnd_id, ))

        cur.executemany("""
            INSERT INTO dnb_old_auth (
                dnb_meta_id, number, prefix, gnd_id
            ) VALUES ((SELECT id FROM dnb_meta WHERE dnb_id = ?), ?, ?, ?)
            """, values)
        con.commit()


def db_import_gaz(con, json):
    """
    Writes single JSON object into SQLite table view which will activate
    an INSTEAD OF INSERT trigger.
    """
    cur = con.cursor()
    cur.execute("INSERT INTO gaz_raw_view (raw) VALUES (json(?))", (json, ))
    con.commit()


def db_open(db_path):
    """
    Opens database, executes PRAGMA statements, and returns connection handle.
    """
    con = sqlite3.connect(db_path)

    if not con:
        logger.error('failed to open database "{}"'.format(db_path))
        return

    db_pragma(con)
    return con


def db_pragma(con):
    """
    Executes SQLite PRAGMA statements for faster import.
    """
    cur = con.cursor()
    cur.execute("PRAGMA journal_mode = OFF")
    cur.execute("PRAGMA synchronous = 0")
    cur.execute("PRAGMA cache_size = 1000000")
    cur.execute("PRAGMA locking_mode = EXCLUSIVE")
    cur.execute("PRAGMA temp_store = MEMORY")
    con.commit()


def json_read(json_path):
    """
    Reads JSON from file and returns data as dictionary.
    """
    data = None

    with open(json_path, 'r') as json_file:
        try:
            data = json.load(json_file)
        except json.JSONDecodeError as e:
            logger.error(str(e))

    return data


def json_import_dnb(json_path, db_path, old_auth=False):
    """
    Imports JSON-LD into SQLite database from given paths.
    """
    # Keys.
    owl_key       = 'http://www.w3.org/2002/07/owl#sameAs'
    pref_name_key = 'https://d-nb.info/standards/elementset/gnd#preferredNameForThePlaceOrGeographicName'
    var_names_key = 'https://d-nb.info/standards/elementset/gnd#variantNameForThePlaceOrGeographicName'
    old_auths_key = 'https://d-nb.info/standards/elementset/gnd#oldAuthorityNumber'

    # Identifiers.
    dnb_ident          = 'https://d-nb.info/gnd/'
    owl_geonames_ident = 'https://sws.geonames.org/'
    owl_gnd_ident      = 'https://d-nb.info/gnd/'
    owl_loc_ident      = 'http://id.loc.gov/rwo/agents/'
    owl_viaf_ident     = 'http://viaf.org/viaf/'
    owl_wikidata_ident = 'http://www.wikidata.org/entity/'

    con = db_open(db_path)
    if not con: return

    logger.debug('reading JSON-LD file "{}" ...'.format(json_path))

    with open(json_path, 'r') as json_file:
        # Read array objects as stream.
        objects = ijson.items(json_file, 'item.item')
        n = 0

        # Parse each object.
        for obj in objects:
            gnd_id       = None
            owl_viaf     = None
            owl_wikidata = None
            owl_loc      = None
            owl_gnd      = None
            owl_geonames = None
            pref_name    = None
            var_names    = None
            old_auths    = None

            # Get @id value.
            obj_id = obj.get('@id')

            if not obj_id:
                logger.debug('object {} has no @id key'.format(n))
                continue

            if not obj_id.startswith(dnb_ident) or obj_id.endswith('/about'):
                logger.debug('ignoring object {}'.format(obj_id))
                continue

            # Get gnd id from @id value.
            dnb_id = obj_id[len(dnb_ident):]

            # Get owl same-as identifiers.
            owl_list = obj.get(owl_key, [])

            if len(owl_list) > 0:
                for owl_obj in owl_list:
                    owl_value = owl_obj.get('@id')
                    if not owl_value: continue

                    if owl_value.startswith(owl_geonames_ident):
                        owl_geonames = owl_value[len(owl_geonames_ident):]

                    if owl_value.startswith(owl_gnd_ident):
                        owl_gnd = owl_value[len(owl_gnd_ident):]

                    if owl_value.startswith(owl_loc_ident):
                        owl_loc = owl_value[len(owl_loc_ident):]

                    if owl_value.startswith(owl_viaf_ident):
                        owl_viaf = owl_value[len(owl_viaf_ident):]

                    if owl_value.startswith(owl_wikidata_ident):
                        owl_wikidata = owl_value[len(owl_wikidata_ident):]

            # Get preferred name.
            pref_list = obj.get(pref_name_key, [])

            if len(pref_list) > 0:
                pref_name = pref_list[0].get('@value')

            # Get variant names.
            var_list = obj.get(var_names_key, [])

            if len(var_list) > 0:
                var_names = []

                for var_obj in var_list:
                    value = var_obj.get('@value')
                    if not value: continue
                    var_names.append((dnb_id, value, ))

            if old_auth:
                # Get old authority numbers.
                var_list = obj.get(old_auths_key, [])

                if len(var_list) > 0:
                    old_auths = []

                    for var_obj in var_list:
                        value = var_obj.get('@value')
                        if not value: continue
                        old_auths.append((dnb_id, value, ))

            # Write to database.
            try:
                logger.debug('importing dnb id {} ({}) ...'.format(dnb_id, n))
                db_import_dnb(con,
                              dnb_id,
                              pref_name,
                              owl_geonames, owl_gnd, owl_loc, owl_viaf, owl_wikidata,
                              var_names,
                              old_auths)
                n = n + 1
                if n % 10000 == 0: logger.info('imported {} objects into "{}"'.format(n, db_path))
            except sqlite3.IntegrityError:
                logger.warning('dnb id {} already exists'.format(dnb_id))

        logger.info('imported {} objects into "{}"'.format(n, db_path))


def json_import_gaz(json_path, db_path):
    """
    Imports JSON into SQLite database from given paths.
    """
    con = db_open(db_path)
    if not con: return

    logger.debug('reading JSON file "{}" ...'.format(json_path))

    with open(json_path, 'r') as json_file:
        objects = ijson.items(json_file, 'item')
        n = 0

        for obj in objects:
            gaz_id = obj.get('gazId')

            if not gaz_id:
                logger.warning('object has to gazId')
                continue

            raw = json.dumps(obj, use_decimal=True)

            try:
                logger.debug('importing gaz id {} ({}) ...'.format(gaz_id, n))
                db_import_gaz(con, raw)
                n = n + 1
                if n % 10000 == 0: logger.info('imported {} objects into "{}"'.format(n, db_path))
            except sqlite3.IntegrityError:
                logger.warning('gaz id {} already exists'.format(gaz_id))

        logger.info('imported {} objects into "{}"'.format(n, db_path))


def parse_args():
    """
    Reads command-line arguments.
    """
    parser = ArgumentParser(description='Gazetteer and DNB database importer', exit_on_error=True)

    parser.add_argument('-o', '--output', help='path to SQLite database file', required=True)
    parser.add_argument('-d', '--dnb',    help='path to DNB JSON-LD file', type=Path)
    parser.add_argument('-g', '--gaz',    help='path to Gazetteer JSON file', type=Path)
    parser.add_argument('-s', '--schema', help='path to SQLite schema file', default='schema.sql')
    parser.add_argument('-O', '--old',    help='import additional old authority numbers (DNB only)', action='store_true')

    group = parser.add_mutually_exclusive_group()
    group.add_argument('-v', '--verbose', help='increase output verbosity', action='store_true')
    group.add_argument('-q', '--quiet',   help='no output except on error', action='store_true')

    args = parser.parse_args()
    return args


def setup_logger(quiet, verbose):
    """
    Configures the global logger.
    """
    level = logging.INFO
    if quiet: level = logging.ERROR
    if verbose: level = logging.DEBUG

    logger.setLevel(level)

    ch = logging.StreamHandler()
    ch.setLevel(level)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)


if __name__ == '__main__':
    # Read command-line arguments and configure logger.
    args = parse_args()
    setup_logger(args.quiet, args.verbose)

    # Create SQLite schema from file.
    db_create_schema(args.output, args.schema)

    try:
        if args.dnb:
            # Import DNB data from JSON-LD file.
            json_import_dnb(json_path=args.dnb, db_path=args.output, old_auth=args.old)

        if args.gaz:
            # Import Gaz data from JSON file.
            json_import_gaz(json_path=args.gaz, db_path=args.output)
    except FileNotFoundError:
        logger.error('input file or schema not found')

