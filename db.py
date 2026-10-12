"""
utils/db.py — PostgreSQL connection helper (replaces mysql-connector-python)
Uses psycopg2 with a connection-per-request pattern (same as the original).
"""

import os
import psycopg2
import psycopg2.extras   # for RealDictCursor (returns rows as dicts)

DB_CONFIG = {
    "host":     os.environ.get("PG_HOST",     "localhost"),
    "port":     int(os.environ.get("PG_PORT", 5432)),
    "user":     os.environ.get("PG_USER",     "postgres"),
    "password": os.environ.get("PG_PASSWORD", ""),
    "dbname":   os.environ.get("PG_DATABASE", "library_db"),
    "sslmode":  os.environ.get("PG_SSLMODE",  "require"),   # Supabase needs SSL
}


DATABASE_URL = os.environ.get("DATABASE_URL")


def get_conn():
    # On Render: one DATABASE_URL (Supabase connection string).
    # Locally: fall back to the PG_* variables above.
    if DATABASE_URL:
        return psycopg2.connect(DATABASE_URL, sslmode="require")
    return psycopg2.connect(**DB_CONFIG)


def run_query(sql, params=None):
    """Run a SELECT and return rows as a list of dicts."""
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params or ())
            rows = cur.fetchall()
    # RealDictRow → plain dict so Flask's jsonify is happy
    return [dict(r) for r in rows]


def run_write(sql, params=None):
    """
    Run an INSERT/UPDATE and return the new row's id.
    Uses RETURNING id for INSERTs; returns None for plain UPDATEs.
    """
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or ())
            try:
                new_id = cur.fetchone()[0]
            except TypeError:
                new_id = None        # UPDATE/DELETE — no RETURNING clause
        conn.commit()
    return new_id
