"""
Postgres helpers (Supabase or any DATABASE_URL).

Usage:
  from db import get_cursor, database_enabled
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator

import psycopg2
from psycopg2.extras import RealDictCursor


def database_enabled() -> bool:
    return bool(os.environ.get("DATABASE_URL", "").strip())


def get_connection():
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(url)


@contextmanager
def get_cursor(dict_rows: bool = False) -> Generator:
    conn = get_connection()
    try:
        factory = RealDictCursor if dict_rows else None
        cur = conn.cursor(cursor_factory=factory)
        try:
            yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()
    finally:
        conn.close()
