
UPGRADES_SQLITE3 = {

    (0,1): [
        "CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);",
        "INSERT INTO meta VALUES('schema_version','1');",
    ],
    (1,2): [
        "CREATE TABLE operation (id INTEGER PRIMARY KEY, type TEXT, start_time TEXT, end_time TEXT);",
        "CREATE TABLE command (id INTEGER PRIMARY KEY, operation_id INTEGER, cmd TEXT, stdin TEXT, stdout TEXT, stderr TEXT);",
        "UPDATE meta SET value='2' where key='schema_version';",
    ],
    (2,3): [
        "ALTER TABLE operation ADD COLUMN failure TEXT;",
        "UPDATE meta SET value='3' where key='schema_version';",
    ],

}