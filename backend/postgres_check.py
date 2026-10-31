"""Run all account tests on a disposable LOCAL PostgreSQL database.
HINGE_TEST_DATABASE_URL must point to localhost/127.0.0.1 and database hinge_test.
Drops the hinge schema in that test database before each test; never uses HINGE_DATABASE_URL.
"""
import os
from pathlib import Path
import tempfile
import unittest
from urllib.parse import urlsplit
import psycopg
from test_server import AccountTests

TARGET = os.environ.get('HINGE_TEST_DATABASE_URL','')
parsed = urlsplit(TARGET)
if parsed.hostname not in ('localhost','127.0.0.1') or parsed.path != '/hinge_test':
    raise SystemExit('Set HINGE_TEST_DATABASE_URL to a disposable LOCAL database named hinge_test')

class PostgreSQLTests(AccountTests):
    def setUp(self):
        with psycopg.connect(TARGET) as db:
            db.execute('DROP SCHEMA IF EXISTS hinge CASCADE')
        self.temp = tempfile.TemporaryDirectory()
        self.db = TARGET
        self.start()

    def start(self):
        from server import make_server
        from test_server import QuietHandler
        import threading
        self.server = make_server('127.0.0.1',0,self.db,seed=True)
        self.server.RequestHandlerClass = QuietHandler
        self.thread = threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()

if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(PostgreSQLTests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
