#!/usr/bin/env python3
"""Capture canonical, read-only SQLite query results for verification."""

from __future__ import annotations

import argparse
import base64
import json
import math
import sqlite3
import sys
from pathlib import Path
from typing import Any, Optional


class SnapshotError(ValueError):
    """Raised when snapshot input is invalid."""


DENIED_ACTIONS = {
    sqlite3.SQLITE_ATTACH,
    sqlite3.SQLITE_ALTER_TABLE,
    sqlite3.SQLITE_CREATE_INDEX,
    sqlite3.SQLITE_CREATE_TABLE,
    sqlite3.SQLITE_CREATE_TEMP_INDEX,
    sqlite3.SQLITE_CREATE_TEMP_TABLE,
    sqlite3.SQLITE_CREATE_TEMP_TRIGGER,
    sqlite3.SQLITE_CREATE_TEMP_VIEW,
    sqlite3.SQLITE_CREATE_TRIGGER,
    sqlite3.SQLITE_CREATE_VIEW,
    sqlite3.SQLITE_DELETE,
    sqlite3.SQLITE_DETACH,
    sqlite3.SQLITE_DROP_INDEX,
    sqlite3.SQLITE_DROP_TABLE,
    sqlite3.SQLITE_DROP_TEMP_INDEX,
    sqlite3.SQLITE_DROP_TEMP_TABLE,
    sqlite3.SQLITE_DROP_TEMP_TRIGGER,
    sqlite3.SQLITE_DROP_TEMP_VIEW,
    sqlite3.SQLITE_DROP_TRIGGER,
    sqlite3.SQLITE_DROP_VIEW,
    sqlite3.SQLITE_INSERT,
    sqlite3.SQLITE_PRAGMA,
    sqlite3.SQLITE_REINDEX,
    sqlite3.SQLITE_TRANSACTION,
    sqlite3.SQLITE_UPDATE,
}


def load_config(path: Path) -> list[dict[str, Any]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SnapshotError(f"cannot read {path}: {error}") from error
    queries = value.get("queries") if isinstance(value, dict) else None
    if not isinstance(queries, list) or not queries:
        raise SnapshotError("config must contain a non-empty queries list")

    names: set[str] = set()
    for query in queries:
        if not isinstance(query, dict):
            raise SnapshotError("each query must be an object")
        name = query.get("name")
        sql = query.get("sql")
        params = query.get("params", [])
        preserve_order = query.get("preserve_order", False)
        if not isinstance(name, str) or not name or name in names:
            raise SnapshotError("query names must be unique non-empty strings")
        if not isinstance(sql, str) or not sql.lstrip().lower().startswith(("select ", "with ")):
            raise SnapshotError(f"query {name} must be a SELECT or WITH statement")
        if ";" in sql.rstrip().rstrip(";"):
            raise SnapshotError(f"query {name} must contain one statement")
        if not isinstance(params, list):
            raise SnapshotError(f"query {name} params must be a list")
        if type(preserve_order) is not bool:
            raise SnapshotError(f"query {name} preserve_order must be boolean")
        names.add(name)
    return queries


def authorizer(
    action: int,
    _arg1: Optional[str],
    _arg2: Optional[str],
    _db: Optional[str],
    _source: Optional[str],
) -> int:
    return sqlite3.SQLITE_DENY if action in DENIED_ACTIONS else sqlite3.SQLITE_OK


def json_value(value: Any) -> Any:
    if isinstance(value, bytes):
        return {"$type": "bytes", "base64": base64.b64encode(value).decode("ascii")}
    if isinstance(value, float) and not math.isfinite(value):
        return {"$type": "float", "value": repr(value)}
    return value


def canonical_rows(cursor: sqlite3.Cursor, preserve_order: bool = False) -> list[dict[str, Any]]:
    columns = [item[0] for item in cursor.description or []]
    if len(columns) != len(set(columns)):
        raise SnapshotError("query result contains duplicate column names")
    rows = [
        {column: json_value(value) for column, value in zip(columns, row)}
        for row in cursor.fetchall()
    ]
    if preserve_order:
        return rows
    return sorted(rows, key=lambda row: json.dumps(row, sort_keys=True, separators=(",", ":")))


def capture(database: Path, config: Path) -> dict[str, Any]:
    if not database.is_file():
        raise SnapshotError(f"database not found: {database}")
    queries = load_config(config)
    uri = f"{database.resolve().as_uri()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.set_authorizer(authorizer)
    try:
        results: dict[str, Any] = {}
        for query in queries:
            try:
                cursor = connection.execute(query["sql"], query.get("params", []))
            except sqlite3.Error as error:
                raise SnapshotError(f"query {query['name']} failed: {error}") from error
            results[query["name"]] = canonical_rows(
                cursor, query.get("preserve_order", False)
            )
    finally:
        connection.close()

    return {"results": results}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    try:
        snapshot = capture(args.db, args.config)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(snapshot, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except (OSError, SnapshotError, sqlite3.Error) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
