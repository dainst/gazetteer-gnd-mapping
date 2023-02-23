#!/usr/bin/env python3

"""
export.py - experimental DNB & Gazetteer data export to HTML5

Usage:

```
$ python3 export.py --help
$ python3 export.py --dnb --input database.sqlite --output dnb.html
$ python3 export.py --gaz --input database.sqlite --output gaz.html
```
"""

import json
import logging
import sqlite3
import sys

from datetime import datetime
from string import Template

from argparse import ArgumentParser, FileType
from pathlib import Path

logger = logging.getLogger('main')

tpl_header = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>$title</title>
    <link rel="stylesheet" href="$css">
</head>
<body>
<main>
<h1>$title</h1>
<hr>
<table>
$thead
<tbody>
"""

tpl_footer = """</tbody>
</table>
<hr>
<p><small>Generated: $dt</small></p>
</main>
</body>
</html>"""


def html_dnb(db_path, html_path, css='style.css', limit=100, title='DNB'):
    """
    Outputs DNB database entries to HTML file.
    """
    logger.debug('Writing entries {} from database "{}" to file "{}" ...'.format(
        limit, db_path, html_path))

    con = sqlite3.connect(db_path)

    if not con:
        logger.error('failed to open database "{}"'.format(db_path))
        return

    cur = con.cursor()

    th = Template(tpl_header)
    tf = Template(tpl_footer)

    today = datetime.now()

    with open(html_path, 'w') as fh:
        thead = '<thead><tr><th>DNB ID</th><th>Pref. Name</th><th>Gaz ID</th></tr></thead>'
        fh.write(th.substitute(
            {
                'title': title,
                'css': css,
                'thead': thead
            }
        ))

        cur.execute(
            """
            SELECT dnb_id, pref_name, owl_gnd FROM dnb_meta ORDER BY dnb_id ASC LIMIT ?
            """, (limit, )
        )
        rows = cur.fetchall()

        html_row = '<tr><td>{}</td><td>{}</td><td>{}</td></tr>\n'
        n = 0

        for row in rows:
            n = n + 1
            line = html_row.format(row[0], row[1], row[2])
            logger.debug('Writing row ({}) ...'.format(n))
            fh.write(line)

        fh.write(tf.substitute({'dt': today.isoformat()}))


def html_gaz(db_path, html_path, css='style.css', limit=100, title='Gazetteer'):
    """
    Outputs Gazetteer database entries to HTML file.
    """
    logger.debug('Writing entries {} from database "{}" to file "{}" ...'.format(
        limit, db_path, html_path))

    con = sqlite3.connect(db_path)

    if not con:
        logger.error('failed to open database "{}"'.format(db_path))
        return

    cur = con.cursor()

    th = Template(tpl_header)
    tf = Template(tpl_footer)

    today = datetime.now()

    with open(html_path, 'w') as fh:
        thead = '<thead><tr><th>Gaz ID</th><th>Pref. Title</th><th>Pref. Lang.</th></tr></thead>'
        fh.write(th.substitute(
            {
                'title': title,
                'css': css,
                'thead': thead
            }
        ))

        cur.execute(
            """
            SELECT gaz_id, pref_title, pref_lang FROM gaz_meta ORDER BY gaz_id ASC LIMIT ?
            """, (limit, )
        )
        rows = cur.fetchall()

        html_row = '<tr><td>{}</td><td>{}</td><td>{}</td></tr>\n'
        n = 0

        for row in rows:
            n = n + 1
            line = html_row.format(row[0], row[1], row[2])
            logger.debug('Writing row ({}) ...'.format(n))
            fh.write(line)

        fh.write(tf.substitute({'dt': today.isoformat()}))


def parse_args():
    """
    Reads command-line arguments.
    """
    parser = ArgumentParser(description='Gazetteer and DNB database exporter', exit_on_error=True)

    parser.add_argument('-i', '--input',   help='path to SQLite database file', required=True, type=Path)
    parser.add_argument('-o', '--output',  help='path of HTML file',            required=True)
    parser.add_argument('-v', '--verbose', help='increase output verbosity',    action='store_true')

    group = parser.add_mutually_exclusive_group()
    group.add_argument('-d', '--dnb', help='select DNB data',       action='store_true')
    group.add_argument('-g', '--gaz', help='select Gazetteer data', action='store_true')

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

    if (args.dnb):
        # Create DNB page.
        html_dnb(args.input, args.output, limit=2000)

    if (args.gaz):
        # Create Gaz page.
        html_gaz(args.input, args.output, limit=2000)

