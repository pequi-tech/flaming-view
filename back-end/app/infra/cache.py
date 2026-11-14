"""Cache chave-valor em SQLite (no lugar de um Redis no MVP)."""
import sqlite3, threading, time
from contextlib import contextmanager


class Cache:
    """Chave-valor com validade em SQLite. Guarda o último valor mesmo vencido, para servir como snapshot se a fonte cair."""

    def __init__(self, path):
        self.path = path
        self.lock = threading.Lock()
        with self._conn() as c:
            c.execute('CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT NOT NULL, stored REAL NOT NULL)')

    @contextmanager
    def _conn(self):
        c = sqlite3.connect(self.path, timeout=10)   # `with sqlite3.connect()` só comita, não fecha
        try:
            with c:
                yield c
        finally:
            c.close()

    def get(self, key):
        """(valor, guardado_em) ou None."""
        with self._conn() as c:
            return c.execute('SELECT value, stored FROM cache WHERE key = ?', (key,)).fetchone()

    def put(self, key, value):
        with self.lock, self._conn() as c:
            c.execute('INSERT OR REPLACE INTO cache VALUES (?, ?, ?)', (key, value, time.time()))
