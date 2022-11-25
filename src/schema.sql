--
-- SQLite 3 database schemas for Gazetteer & DNB meta data.
--

--
-- Gazetteer schema.
--

-- Gazetteer data in JSON format.
CREATE TABLE IF NOT EXISTS gaz_raw (
    id          INTEGER PRIMARY KEY,
    raw         JSON
);

CREATE VIEW IF NOT EXISTS gaz_raw_view AS SELECT * FROM gaz_raw;

-- Gazetteer name data.
CREATE TABLE IF NOT EXISTS gaz_name (
    id          INTEGER PRIMARY KEY,
    gaz_id      INTEGER NOT NULL,
    title       TEXT,
    lang        TEXT
);

-- Additional indices.
CREATE INDEX IF NOT EXISTS idx_gaz_name_gaz_id ON gaz_name (gaz_id);
CREATE INDEX IF NOT EXISTS idx_gaz_name_title  ON gaz_name (gaz_id, title);
CREATE INDEX IF NOT EXISTS idx_gaz_name_lang   ON gaz_name (gaz_id, lang);

-- Gazeteer indentifiers.

-- GeoNames.
CREATE TABLE IF NOT EXISTS gaz_ident_geonames (
    id          INTEGER PRIMARY KEY,
    gaz_id      INTEGER NOT NULL,
    geonames_id INTEGER
);

-- GND ID.
CREATE TABLE IF NOT EXISTS gaz_ident_gnd (
    id          INTEGER PRIMARY KEY,
    gaz_id      INTEGER NOT NULL,
    gnd_id      TEXT
);

-- Zenon System Nr.
CREATE TABLE IF NOT EXISTS gaz_ident_zenon_systemnr (
    id          INTEGER PRIMARY KEY,
    gaz_id      INTEGER NOT NULL,
    zenon_id    TEXT
);

-- Zenon Thesaurus.
CREATE TABLE IF NOT EXISTS gaz_ident_zenon_thesaurus (
    id          INTEGER PRIMARY KEY,
    gaz_id      INTEGER NOT NULL,
    zenon_id    TEXT
);

-- Gazetteer meta data.
CREATE TABLE IF NOT EXISTS gaz_meta (
    id          INTEGER PRIMARY KEY,
    gaz_id      INTEGER NOT NULL,
    pref_title  TEXT,
    pref_lang   TEXT
);

-- Additional indices.
CREATE INDEX IF NOT EXISTS idx_gaz_meta_gaz_id     ON gaz_meta (gaz_id);
CREATE INDEX IF NOT EXISTS idx_gaz_meta_pref_title ON gaz_meta (gaz_id, pref_title);
CREATE INDEX IF NOT EXISTS idx_gaz_meta_pref_lang  ON gaz_meta (gaz_id, pref_lang);

--
-- JSON import triggers. The raw JSON data will be discarded, as the trigger
-- is added to the view.
--
CREATE TRIGGER IF NOT EXISTS gaz_raw_view_ins
    INSTEAD OF INSERT ON gaz_raw_view
    BEGIN
        -- Add meta data to gaz_meta table.
        INSERT INTO gaz_meta (
            gaz_id,
            pref_title,
            pref_lang
        )
        VALUES (
            json_extract(NEW.raw, '$.gazId'),
            json_extract(NEW.raw, '$.prefName.title'),
            json_extract(NEW.raw, '$.prefName.language')
        );

        -- Add titles to gaz_name table.
        INSERT INTO gaz_name (
            gaz_id,
            title,
            lang
        )
        SELECT
            json_extract(New.raw, '$.gazId'),
            json_extract(json_each.value, '$.title'),
            json_extract(json_each.value, '$.language')
        FROM
            json_each(NEW.raw, '$.names');

        -- Add identifiers to gaz_ident_* tables.
        -- GeoNames
        INSERT INTO gaz_ident_geonames (
            gaz_id,
            geonames_id
        )
        SELECT
            json_extract(New.raw, '$.gazId'),
            json_extract(json_each.value, '$.value')
        FROM
            json_each(NEW.raw, '$.identifiers')
        WHERE
            json_extract(json_each.value, '$.context') = 'geonames';

        -- GND ID
        INSERT INTO gaz_ident_gnd (
            gaz_id,
            gnd_id
        )
        SELECT
            json_extract(New.raw, '$.gazId'),
            json_extract(json_each.value, '$.value')
        FROM
            json_each(NEW.raw, '$.identifiers')
        WHERE
            json_extract(json_each.value, '$.context') = 'GND-ID';

        -- Zenon Thesaurus
        INSERT INTO gaz_ident_zenon_thesaurus (
            gaz_id,
            zenon_id
        )
        SELECT
            json_extract(New.raw, '$.gazId'),
            json_extract(json_each.value, '$.value')
        FROM
            json_each(NEW.raw, '$.identifiers')
        WHERE
            json_extract(json_each.value, '$.context') = 'zenon-thesaurus';

        -- Zenon System Nr.
        INSERT INTO gaz_ident_zenon_systemnr (
            gaz_id,
            zenon_id
        )
        SELECT
            json_extract(New.raw, '$.gazId'),
            json_extract(json_each.value, '$.value')
        FROM
            json_each(NEW.raw, '$.identifiers')
        WHERE
            json_extract(json_each.value, '$.context') = 'zenon-systemnr';
    END;

--
-- DNB schema.
--
CREATE TABLE IF NOT EXISTS dnb_meta (
    id              INTEGER PRIMARY KEY,
    dnb_id          TEXT,
    pref_name       TEXT,
    owl_geonames    INTEGER,
    owl_gnd         TEXT,
    owl_loc         TEXT,
    owl_viaf        INTEGER,
    owl_wikidata    TEXT
);

-- variantNameForThePlaceOrGeographicName
CREATE TABLE IF NOT EXISTS dnb_name (
    id          INTEGER PRIMARY KEY,
    dnb_meta_id INTEGER NOT NULL,
    var_name    TEXT,
    FOREIGN KEY (dnb_meta_id) REFERENCES dnb_meta(id)
);

-- oldAuthorityNumber
CREATE TABLE IF NOT EXISTS dnb_old_auth (
    id          INTEGER PRIMARY KEY,
    dnb_meta_id INTEGER NOT NULL,
    number      TEXT,
    prefix      TEXT,
    gnd_id      TEXT,
    FOREIGN KEY (dnb_meta_id) REFERENCES dnb_meta(id)
);
