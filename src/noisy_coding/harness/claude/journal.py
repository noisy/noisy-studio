"""Durable attempt history: commit before I/O, never replay an ambiguous write."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sqlite3
import threading

from noisy_coding.harness.provider import Receipt, Speech


class Journal:
    def __init__(self, path: Path | None = None):
        self._path = path
        self._connection = None
        self._lock = threading.RLock()

    def _db(self):
        if self._connection is None:
            if self._path:
                self._path.parent.mkdir(parents=True, exist_ok=True)
                self._path.touch(mode=0o600, exist_ok=True)
            self._connection = sqlite3.connect(str(self._path) if self._path else ':memory:', check_same_thread=False)
            self._connection.execute('PRAGMA synchronous=FULL')
            self._connection.execute('CREATE TABLE IF NOT EXISTS deliveries (id TEXT PRIMARY KEY, speech TEXT NOT NULL, state TEXT NOT NULL, detail TEXT NOT NULL)')
            self._connection.commit()
        return self._connection

    @staticmethod
    def key(speech: Speech) -> str:
        identity = [speech.conversation, speech.utterance_id, float(speech.created_at)]
        return hashlib.sha256(json.dumps(identity).encode()).hexdigest()

    def add(self, speech: Speech) -> Receipt:
        with self._lock:
            db = self._db()
            db.execute('INSERT OR IGNORE INTO deliveries VALUES (?, ?, ?, ?)',
                       (self.key(speech), json.dumps(asdict(speech)), 'queued', ''))
            db.commit()
            state, detail = db.execute('SELECT state, detail FROM deliveries WHERE id=?', (self.key(speech),)).fetchone()
            return Receipt(speech.utterance_id, speech.conversation, state, detail)

    def record(self, speeches: list[Speech], state: str, detail: str) -> None:
        with self._lock:
            db = self._db()
            db.executemany('UPDATE deliveries SET state=?, detail=? WHERE id=?',
                           [(state, detail, self.key(s)) for s in speeches])
            db.commit()

    def entries(self, state: str | None = None) -> list[tuple[Speech, Receipt]]:
        with self._lock:
            query = 'SELECT speech, state, detail FROM deliveries'
            if state is not None:
                query += ' WHERE state=?'
            rows = self._db().execute(query + ' ORDER BY rowid', (state,) if state is not None else ()).fetchall()
            result = []
            for raw, state, detail in rows:
                speech = Speech(**json.loads(raw))
                result.append((speech, Receipt(speech.utterance_id, speech.conversation, state, detail)))
            return result

    def claim(self, speeches: list[Speech]) -> list[Speech]:
        with self._lock:
            db = self._db()
            claimed = []
            for speech in speeches:
                result = db.execute("UPDATE deliveries SET state='uncertain', detail='send attempt started; outcome unknown' WHERE id=? AND state='queued'", (self.key(speech),))
                if result.rowcount:
                    claimed.append(speech)
            db.commit()
            return claimed

    def cancel(self, speech: Speech) -> bool:
        with self._lock:
            db = self._db()
            inserted = db.execute('INSERT OR IGNORE INTO deliveries VALUES (?, ?, ?, ?)',
                                  (self.key(speech), json.dumps(asdict(speech)), 'cancelled', 'cancelled by user'))
            result = db.execute("UPDATE deliveries SET state='cancelled', detail='cancelled by user' WHERE id=? AND state IN ('queued','unavailable','rejected','cancelled')", (self.key(speech),))
            db.commit()
            return bool(inserted.rowcount or result.rowcount)
