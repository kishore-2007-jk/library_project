"""
app.py — Library Management System (PostgreSQL / Supabase version)
Migrated from MySQL. Key changes:
  - mysql.connector  → utils.db (psycopg2)
  - %s placeholders stay the same (psycopg2 uses %s too)
  - DATE_FORMAT(...)      → TO_CHAR(..., 'YYYY-MM-DD')
  - CURDATE()             → CURRENT_DATE
  - DATE_ADD(d, INTERVAL) → d + INTERVAL '...'
  - DATEDIFF(a,b)         → (a - b)  (returns int in Postgres)
  - GREATEST(...)         → GREATEST(...)  (same)
  - lastrowid             → RETURNING id  (handled in run_write)
  - tinyint 0/1 booleans  → real Python booleans from psycopg2
"""

import os
from flask import Flask, jsonify, request, send_from_directory
from utils.db import run_query, run_write
import psycopg2

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret")

FINE_PER_DAY = 2   # rupees per late day
MAX_BOOKS    = 3   # books one member can hold at a time


# ── Static ────────────────────────────────────────────────────────────────────

@app.route("/")
def home():
    return send_from_directory("static", "index.html")


# ── READ routes ───────────────────────────────────────────────────────────────

@app.route("/api/dashboard")
def dashboard():
    sql = """
    SELECT
      (SELECT COUNT(*) FROM Books)   AS total_titles,
      (SELECT COUNT(*) FROM Members) AS members,
      (SELECT COUNT(*) FROM Issues WHERE return_date IS NULL) AS currently_issued,
      (SELECT COUNT(*) FROM Issues
       WHERE return_date IS NULL AND due_date < CURRENT_DATE) AS overdue
    """
    return jsonify(run_query(sql)[0])


@app.route("/api/books")
def books():
    search = request.args.get("search", "")
    like = f"%{search}%"
    sql = """
    SELECT b.book_id, b.title, a.name AS author, c.name AS category,
           b.total_copies, b.available_copies
    FROM Books b
    JOIN Authors    a ON b.author_id   = a.author_id
    JOIN Categories c ON b.category_id = c.category_id
    WHERE b.title ILIKE %s OR a.name ILIKE %s
    ORDER BY b.title
    """
    # ILIKE = case-insensitive LIKE (Postgres-native, replaces MySQL's default)
    return jsonify(run_query(sql, (like, like)))


@app.route("/api/members")
def members():
    sql = """
    SELECT member_id, name, email, phone,
           TO_CHAR(join_date, 'YYYY-MM-DD') AS join_date
    FROM Members ORDER BY member_id
    """
    return jsonify(run_query(sql))


@app.route("/api/issued")
def issued():
    sql = """
    SELECT i.issue_id, i.renewed, b.title, m.name AS member,
           TO_CHAR(i.issue_date, 'YYYY-MM-DD') AS issue_date,
           TO_CHAR(i.due_date,   'YYYY-MM-DD') AS due_date
    FROM Issues i
    JOIN Books   b ON i.book_id   = b.book_id
    JOIN Members m ON i.member_id = m.member_id
    WHERE i.return_date IS NULL
    ORDER BY i.due_date
    """
    return jsonify(run_query(sql))


@app.route("/api/overdue")
def overdue():
    sql = """
    SELECT i.issue_id, m.name AS member, m.phone, b.title,
           TO_CHAR(i.due_date, 'YYYY-MM-DD') AS due_date,
           (CURRENT_DATE - i.due_date)                AS days_overdue,
           (CURRENT_DATE - i.due_date) * %s::numeric  AS fine_so_far
    FROM Issues i
    JOIN Books   b ON i.book_id   = b.book_id
    JOIN Members m ON i.member_id = m.member_id
    WHERE i.return_date IS NULL AND i.due_date < CURRENT_DATE
    ORDER BY days_overdue DESC
    """
    return jsonify(run_query(sql, (FINE_PER_DAY,)))


@app.route("/api/fines")
def fines():
    sql = """
    SELECT f.fine_id, m.name AS member, b.title,
           f.amount, f.paid
    FROM Fines f
    JOIN Issues  i ON f.issue_id  = i.issue_id
    JOIN Books   b ON i.book_id   = b.book_id
    JOIN Members m ON i.member_id = m.member_id
    """
    rows = run_query(sql)
    for r in rows:
        r["amount"] = float(r["amount"])   # Decimal → float for JSON
    return jsonify(rows)


@app.route("/api/due_soon")
def due_soon():
    sql = """
    SELECT i.issue_id, m.name AS member, m.phone, b.title,
           TO_CHAR(i.due_date, 'YYYY-MM-DD') AS due_date,
           (i.due_date - CURRENT_DATE) AS days_left
    FROM Issues i
    JOIN Books   b ON i.book_id   = b.book_id
    JOIN Members m ON i.member_id = m.member_id
    WHERE i.return_date IS NULL
      AND i.due_date BETWEEN CURRENT_DATE
                         AND CURRENT_DATE + INTERVAL '3 days'
    ORDER BY i.due_date
    """
    return jsonify(run_query(sql))


@app.route("/api/popular")
def popular():
    sql = """
    SELECT b.title, a.name AS author, COUNT(i.issue_id) AS times_issued
    FROM Books b
    JOIN Authors a ON b.author_id = a.author_id
    LEFT JOIN Issues i ON b.book_id = i.book_id
    GROUP BY b.book_id, b.title, a.name
    ORDER BY times_issued DESC, b.title
    LIMIT 5
    """
    return jsonify(run_query(sql))


# ── WRITE routes ──────────────────────────────────────────────────────────────

@app.route("/api/members", methods=["POST"])
def add_member():
    data = request.get_json()
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400
    try:
        run_write(
            "INSERT INTO Members (name, email, phone) VALUES (%s, %s, %s)",
            (name, data.get("email") or None, data.get("phone") or None),
        )
    except psycopg2.errors.UniqueViolation:
        return jsonify({"error": "A member with this email already exists"}), 400
    return jsonify({"message": "Member added"})


@app.route("/api/issue", methods=["POST"])
def issue_book():
    data = request.get_json()
    book_id, member_id = data.get("book_id"), data.get("member_id")

    book = run_query("SELECT available_copies FROM Books WHERE book_id = %s", (book_id,))
    if not book:
        return jsonify({"error": "Book not found"}), 404
    if book[0]["available_copies"] < 1:
        return jsonify({"error": "No copies available"}), 400
    if not run_query("SELECT 1 FROM Members WHERE member_id = %s", (member_id,)):
        return jsonify({"error": "Member not found"}), 404

    held = run_query(
        "SELECT COUNT(*) AS n FROM Issues WHERE member_id = %s AND return_date IS NULL",
        (member_id,))[0]["n"]
    if int(held) >= MAX_BOOKS:
        return jsonify({"error": f"Limit reached: member already holds {MAX_BOOKS} books"}), 400

    same = run_query(
        "SELECT 1 FROM Issues WHERE member_id = %s AND book_id = %s AND return_date IS NULL",
        (member_id, book_id))
    if same:
        return jsonify({"error": "Member already has a copy of this book"}), 400

    unpaid = run_query(
        "SELECT COUNT(*) AS n FROM Fines f "
        "JOIN Issues i ON f.issue_id = i.issue_id "
        "WHERE i.member_id = %s AND f.paid = FALSE", (member_id,))[0]["n"]
    if int(unpaid) > 0:
        return jsonify({"error": "Member has unpaid fines. Clear them first"}), 400

    # Trigger trg_issue_book lowers available_copies automatically
    run_write(
        "INSERT INTO Issues (book_id, member_id, due_date) "
        "VALUES (%s, %s, CURRENT_DATE + INTERVAL '14 days')",
        (book_id, member_id),
    )
    return jsonify({"message": "Book issued for 14 days"})


@app.route("/api/return", methods=["POST"])
def return_book():
    issue_id = request.get_json().get("issue_id")

    rows = run_query("SELECT return_date FROM Issues WHERE issue_id = %s", (issue_id,))
    if not rows:
        return jsonify({"error": "Issue record not found"}), 404
    if rows[0]["return_date"] is not None:
        return jsonify({"error": "This book is already returned"}), 400

    # Trigger trg_return_book raises available_copies automatically
    run_write("UPDATE Issues SET return_date = CURRENT_DATE WHERE issue_id = %s", (issue_id,))

    late = run_query(
        "SELECT GREATEST((return_date - due_date), 0) AS late_days "
        "FROM Issues WHERE issue_id = %s", (issue_id,)
    )[0]["late_days"]
    fine = int(late) * FINE_PER_DAY
    if fine > 0:
        run_write("INSERT INTO Fines (issue_id, amount) VALUES (%s, %s)", (issue_id, fine))
    return jsonify({"message": "Book returned", "fine": fine})


@app.route("/api/pay_fine", methods=["POST"])
def pay_fine():
    fine_id = request.get_json().get("fine_id")
    rows = run_query("SELECT paid FROM Fines WHERE fine_id = %s", (fine_id,))
    if not rows:
        return jsonify({"error": "Fine not found"}), 404
    if rows[0]["paid"]:           # psycopg2 returns True/False, not 0/1
        return jsonify({"error": "Fine already paid"}), 400
    run_write("UPDATE Fines SET paid = TRUE WHERE fine_id = %s", (fine_id,))
    return jsonify({"message": "Fine marked as paid"})


@app.route("/api/renew", methods=["POST"])
def renew_book():
    issue_id = request.get_json().get("issue_id")
    rows = run_query(
        "SELECT return_date, renewed, due_date < CURRENT_DATE AS is_overdue "
        "FROM Issues WHERE issue_id = %s", (issue_id,))
    if not rows:
        return jsonify({"error": "Issue record not found"}), 404
    r = rows[0]
    if r["return_date"] is not None:
        return jsonify({"error": "This book is already returned"}), 400
    if r["renewed"]:              # True/False boolean from psycopg2
        return jsonify({"error": "This book was already renewed once"}), 400
    if r["is_overdue"]:
        return jsonify({"error": "Overdue books cannot be renewed. Return it first"}), 400

    run_write(
        "UPDATE Issues "
        "SET due_date = due_date + INTERVAL '7 days', renewed = TRUE "
        "WHERE issue_id = %s", (issue_id,))
    return jsonify({"message": "Renewed for 7 more days"})


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(debug=debug)
