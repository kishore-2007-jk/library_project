# Library Management System

Flask + PostgreSQL (Supabase) · Deployed on Render

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # fill in your Supabase credentials
python app.py
```

## Database setup (Supabase)

1. Create a new project at https://supabase.com
2. Go to **SQL Editor** and run `schema.sql`
3. Then run `seed.sql`

## Deploy to Render

1. Push this folder to GitHub (without `.venv/` and `.env`)
2. Create a **Web Service** on https://render.com
   - Build command : `pip install -r requirements.txt`
   - Start command : `gunicorn app:app`
3. Add environment variables (Settings → Environment):
   | Key | Value |
   |-----|-------|
   | `FLASK_SECRET_KEY` | any random string |
   | `FLASK_DEBUG` | `0` |
   | `PG_HOST` | from Supabase project settings |
   | `PG_PORT` | `5432` |
   | `PG_USER` | `postgres` |
   | `PG_PASSWORD` | your Supabase DB password |
   | `PG_DATABASE` | `postgres` |
   | `PG_SSLMODE` | `require` |

> **Note:** Render free-tier web services spin down after 15 min of inactivity.
> The first request after idle takes ~30 seconds to wake up.

## What changed from MySQL

| MySQL | PostgreSQL |
|-------|-----------|
| `mysql-connector-python` | `psycopg2-binary` |
| `AUTO_INCREMENT` | `SERIAL` |
| `CURDATE()` | `CURRENT_DATE` |
| `DATE_FORMAT(d, '%Y-%m-%d')` | `TO_CHAR(d, 'YYYY-MM-DD')` |
| `DATE_ADD(d, INTERVAL 14 DAY)` | `d + INTERVAL '14 days'` |
| `DATEDIFF(a, b)` | `(a - b)` (returns integer) |
| `LIKE` (case-insensitive by default) | `ILIKE` |
| `TINYINT(1)` booleans (0/1) | `BOOLEAN` (True/False) |
| `cur.lastrowid` | `RETURNING id` via `run_write()` |
| `IntegrityError` from mysql.connector | `psycopg2.errors.UniqueViolation` |
| `DELIMITER //` in triggers | Standard Postgres `$$` syntax |
