"""SQLite implementation of the existing async ReportStore interface.

Each operation owns a connection in a worker thread. No new package dependency;
transactions avoid lost updates across connections. Startup task recovery is intended
for a single application worker and never automatically replays paid research.
"""

import asyncio
from contextlib import closing
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3


class SQLiteReportStore:
    def __init__(self, path: Path):
        self._path = path

    def _call(self, operation):
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with closing(sqlite3.connect(str(self._path), timeout=5)) as connection:
                connection.execute("CREATE TABLE IF NOT EXISTS reports (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
                with connection:
                    return operation(connection)
        except sqlite3.Error:
            raise OSError("SQLite report store unavailable") from None

    @staticmethod
    def _decode(payload):
        record = json.loads(payload)
        if not isinstance(record, dict):
            raise ValueError("Invalid stored report")
        return record

    async def list_reports(self, report_ids: list[str] | None = None) -> list[dict]:
        def read(connection):
            if report_ids is not None:
                records = []
                for report_id in report_ids:
                    row = connection.execute("SELECT payload FROM reports WHERE id = ?", (report_id,)).fetchone()
                    if row:
                        records.append(self._decode(row[0]))
                return records
            return [self._decode(row[0]) for row in connection.execute("SELECT payload FROM reports ORDER BY id")]
        return await asyncio.to_thread(self._call, read)

    async def get_report(self, report_id: str) -> dict | None:
        def read(connection):
            row = connection.execute("SELECT payload FROM reports WHERE id = ?", (report_id,)).fetchone()
            return self._decode(row[0]) if row else None
        return await asyncio.to_thread(self._call, read)

    async def upsert_report(self, report_id: str, report: dict) -> None:
        payload = json.dumps(report, ensure_ascii=False, allow_nan=False)
        def write(connection):
            connection.execute("INSERT INTO reports (id, payload) VALUES (?, ?) "
                               "ON CONFLICT(id) DO UPDATE SET payload=excluded.payload", (report_id, payload))
        await asyncio.to_thread(self._call, write)

    async def delete_report(self, report_id: str) -> bool:
        def delete(connection):
            return connection.execute("DELETE FROM reports WHERE id = ?", (report_id,)).rowcount > 0
        return await asyncio.to_thread(self._call, delete)

    async def recover_running(self) -> int:
        def recover(connection):
            connection.execute("BEGIN IMMEDIATE")
            count = 0
            for report_id, payload in connection.execute("SELECT id, payload FROM reports").fetchall():
                record = self._decode(payload)
                if record.get("status") == "running":
                    record.update(status="interrupted", error_code="process_restarted",
                                  updated_at=datetime.now(timezone.utc).isoformat())
                    connection.execute("UPDATE reports SET payload = ? WHERE id = ?",
                                       (json.dumps(record, ensure_ascii=False), report_id))
                    count += 1
            return count
        return await asyncio.to_thread(self._call, recover)

    async def check_health(self) -> None:
        def check(connection):
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("SELECT count(*) FROM reports").fetchone()
        await asyncio.to_thread(self._call, check)
