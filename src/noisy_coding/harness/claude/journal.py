"""Durable attempt history: commit before I/O, never replay an ambiguous write."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sqlite3
import threading
import time

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
            self._connection.execute('CREATE TABLE IF NOT EXISTS wake_requests (prompt TEXT PRIMARY KEY, conversation TEXT NOT NULL, state TEXT NOT NULL)')
            columns = {row[1] for row in self._connection.execute('PRAGMA table_info(deliveries)')}
            if 'written_at' not in columns:
                self._connection.execute('ALTER TABLE deliveries ADD COLUMN written_at REAL')
            self._connection.commit()
        return self._connection

    @staticmethod
    def key(speech: Speech) -> str:
        identity = [speech.conversation, speech.utterance_id, float(speech.created_at)]
        return hashlib.sha256(json.dumps(identity).encode()).hexdigest()

    def claim_wake(self, conversation: str, prompt: str) -> bool:
        with self._lock:
            db = self._db()
            if db.execute("SELECT 1 FROM wake_requests WHERE conversation=? AND state IN ('uncertain','requested')", (conversation,)).fetchone():
                return False
            db.execute("INSERT INTO wake_requests VALUES (?, ?, 'uncertain')", (prompt, conversation))
            db.commit()
            return True

    def finish_wake(self, prompt: str, state: str) -> None:
        with self._lock:
            db = self._db()
            db.execute("UPDATE wake_requests SET state=? WHERE prompt=? AND state!='handled'", (state, prompt))
            db.commit()

    def accept_wake(self, conversation: str, prompt: str) -> bool:
        with self._lock:
            db = self._db()
            row = db.execute('SELECT 1 FROM wake_requests WHERE conversation=? AND prompt=?', (conversation, prompt)).fetchone()
            if row is None:
                return False
            db.execute("UPDATE wake_requests SET state='handled' WHERE prompt=?", (prompt,))
            db.commit()
            return True

    def retire_wakes(self, conversation: str) -> None:
        with self._lock:
            db = self._db()
            db.execute("UPDATE wake_requests SET state='retired' WHERE conversation=? AND state IN ('requested','uncertain')", (conversation,))
            db.commit()

    def add(self, speech: Speech) -> Receipt:
        with self._lock:
            db = self._db()
            db.execute('INSERT OR IGNORE INTO deliveries (id, speech, state, detail) VALUES (?, ?, ?, ?)',
                       (self.key(speech), json.dumps(asdict(speech)), 'queued', ''))
            db.commit()
            state, detail = db.execute('SELECT state, detail FROM deliveries WHERE id=?', (self.key(speech),)).fetchone()
            return Receipt(speech.utterance_id, speech.conversation, state, detail)

    def record(self, speeches: list[Speech], state: str, detail: str, *, written_at: float | None = None) -> None:
        with self._lock:
            db = self._db()
            timestamp = (time.time() if written_at is None else written_at) if state == 'sent' else None
            db.executemany("UPDATE deliveries SET state=?, detail=?, written_at=COALESCE(?, written_at) WHERE id=? AND state!='confirmed'",
                           [(state, detail, timestamp, self.key(s)) for s in speeches])
            db.commit()

    def acknowledge(self, conversation: str, message_ids: list[str]) -> list[tuple[Speech, Receipt]]:
        with self._lock:
            db = self._db()
            confirmed = []
            for message_id in dict.fromkeys(message_ids):
                row = db.execute('SELECT speech, state FROM deliveries WHERE id=?', (message_id,)).fetchone()
                if row is None:
                    continue
                speech = Speech(**json.loads(row[0]))
                if speech.conversation != conversation or row[1] not in ('sent', 'unknown', 'uncertain', 'confirmed'):
                    continue
                detail = 'Receiving agent acknowledged this message; task completion is separate.'
                db.execute("UPDATE deliveries SET state='confirmed', detail=? WHERE id=?", (detail, message_id))
                confirmed.append((speech, Receipt(speech.utterance_id, conversation, 'confirmed', detail, message_id=message_id)))
            db.commit()
            return confirmed

    def expire_sent(self, cutoff: float, detail: str) -> list[tuple[Speech, Receipt]]:
        """Bound unconfirmed status without turning missing evidence into failure."""
        with self._lock:
            db = self._db()
            rows = db.execute("UPDATE deliveries SET state='unknown', detail=? WHERE state='sent' AND (written_at IS NULL OR written_at<=?) RETURNING speech", (detail, cutoff)).fetchall()
            db.commit()
            speeches = [Speech(**json.loads(row[0])) for row in rows]
            return [(speech, Receipt(speech.utterance_id, speech.conversation, 'unknown', detail)) for speech in speeches]

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
            inserted = db.execute('INSERT OR IGNORE INTO deliveries (id, speech, state, detail) VALUES (?, ?, ?, ?)',
                                  (self.key(speech), json.dumps(asdict(speech)), 'cancelled', 'cancelled by user'))
            result = db.execute("UPDATE deliveries SET state='cancelled', detail='cancelled by user' WHERE id=? AND state IN ('queued','unavailable','rejected','cancelled')", (self.key(speech),))
            db.commit()
            return bool(inserted.rowcount or result.rowcount)
