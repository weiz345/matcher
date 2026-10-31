"""SQLite / Supabase PostgreSQL connection adapter; credentials stay server-side."""
import re
import sqlite3

POSTGRES_PREFIXES = ('postgres://', 'postgresql://')

def is_postgres(value): return str(value).startswith(POSTGRES_PREFIXES)

class Record(dict):
    """Supports the existing database code's named and positional row reads."""
    def __getitem__(self, key):
        if isinstance(key, int): return tuple(self.values())[key]
        return super().__getitem__(key)

def row_factory(cursor):
    names = [column.name for column in cursor.description] if cursor.description else []
    return lambda values: Record(zip(names, values))

def postgres_sql(sql):
    sql = sql.strip()
    if sql.upper() == 'BEGIN IMMEDIATE': return 'BEGIN'
    ignore = re.match(r'INSERT\s+OR\s+IGNORE\s+INTO\b', sql, re.I)
    if ignore:
        sql = re.sub(r'INSERT\s+OR\s+IGNORE\s+INTO\b', 'INSERT INTO', sql, count=1, flags=re.I)
        sql = sql.rstrip(';') + ' ON CONFLICT DO NOTHING'
    sql = sql.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'BIGSERIAL PRIMARY KEY')
    sql = re.sub(r'\bBLOB\b', 'BYTEA', sql)
    return sql.replace('?', '%s')

class PostgreSQL:
    def __init__(self, dsn):
        try:
            import psycopg
        except ImportError:
            raise RuntimeError('PostgreSQL needs psycopg: install backend/requirements-postgres.txt') from None
        self.driver = psycopg
        # Do not log DSNs or include driver errors containing credentials.
        try:
            self.db = psycopg.connect(dsn, row_factory=row_factory, connect_timeout=10)
            self.db.execute('SET search_path TO hinge')
            self.db.execute("SET statement_timeout TO '15s'")
            self.db.commit()
        except psycopg.Error:
            raise sqlite3.OperationalError('PostgreSQL connection/setup failed') from None

    def execute(self, sql, parameters=()):
        if sql.strip().upper().startswith('PRAGMA '): return self.db.execute('SELECT 1')
        try:
            if sql.strip().upper() == 'BEGIN IMMEDIATE':
                # Psycopg starts the transaction implicitly. Serialize API writes.
                return self.db.execute('SELECT pg_advisory_xact_lock(723194042)')
            return self.db.execute(postgres_sql(sql), parameters)
        except self.driver.IntegrityError:
            raise sqlite3.IntegrityError('Database constraint failed') from None
        except self.driver.Error:
            raise sqlite3.OperationalError('PostgreSQL query failed') from None

    def executescript(self, script):
        # Only used with this application's static table/index DDL (no functions).
        for statement in script.split(';'):
            if statement.strip(): self.execute(statement)

    def executemany(self, sql, rows):
        try:
            cursor = self.db.cursor()
            cursor.executemany(postgres_sql(sql), rows)
            return cursor
        except self.driver.Error:
            raise sqlite3.OperationalError('PostgreSQL batch failed') from None

    def commit(self):
        try: self.db.commit()
        except self.driver.Error: raise sqlite3.OperationalError('PostgreSQL commit failed') from None
    def rollback(self): self.db.rollback()
    def close(self): self.db.close()
    def __enter__(self): return self
    def __exit__(self, kind, value, traceback):
        try:
            if kind is None: self.commit()
            else: self.db.rollback()
        finally: self.db.close()


def connect_database(target):
    if is_postgres(target): return PostgreSQL(str(target))
    db = sqlite3.connect(target, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    return db
