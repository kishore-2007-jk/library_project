-- PostgreSQL schema (migrated from MySQL)
-- Run this in Supabase SQL Editor or psql

-- Drop tables in reverse FK order
DROP TABLE IF EXISTS Fines    CASCADE;
DROP TABLE IF EXISTS Issues   CASCADE;
DROP TABLE IF EXISTS Books    CASCADE;
DROP TABLE IF EXISTS Members  CASCADE;
DROP TABLE IF EXISTS Categories CASCADE;
DROP TABLE IF EXISTS Authors  CASCADE;

-- ── Authors ──────────────────────────────────────────
CREATE TABLE Authors (
    author_id SERIAL PRIMARY KEY,
    name      VARCHAR(100) NOT NULL
);

-- ── Categories ───────────────────────────────────────
CREATE TABLE Categories (
    category_id SERIAL PRIMARY KEY,
    name        VARCHAR(50) NOT NULL UNIQUE
);

-- ── Members ──────────────────────────────────────────
CREATE TABLE Members (
    member_id SERIAL PRIMARY KEY,
    name      VARCHAR(100) NOT NULL,
    email     VARCHAR(100) UNIQUE,
    phone     VARCHAR(15),
    join_date DATE NOT NULL DEFAULT CURRENT_DATE
);

-- ── Books ────────────────────────────────────────────
CREATE TABLE Books (
    book_id          SERIAL PRIMARY KEY,
    title            VARCHAR(150) NOT NULL,
    author_id        INT NOT NULL REFERENCES Authors(author_id),
    category_id      INT NOT NULL REFERENCES Categories(category_id),
    isbn             VARCHAR(20) UNIQUE,
    total_copies     INT NOT NULL CHECK (total_copies >= 0),
    available_copies INT NOT NULL CHECK (available_copies >= 0)
);

-- ── Issues ───────────────────────────────────────────
CREATE TABLE Issues (
    issue_id    SERIAL PRIMARY KEY,
    book_id     INT  NOT NULL REFERENCES Books(book_id),
    member_id   INT  NOT NULL REFERENCES Members(member_id),
    issue_date  DATE NOT NULL DEFAULT CURRENT_DATE,
    due_date    DATE NOT NULL,
    return_date DATE,
    renewed     BOOLEAN NOT NULL DEFAULT FALSE
);

-- ── Fines ────────────────────────────────────────────
CREATE TABLE Fines (
    fine_id  SERIAL PRIMARY KEY,
    issue_id INT            NOT NULL REFERENCES Issues(issue_id),
    amount   NUMERIC(8,2)   NOT NULL CHECK (amount >= 0),
    paid     BOOLEAN        NOT NULL DEFAULT FALSE
);

-- ── Triggers (replace MySQL triggers) ───────────────

-- Decrease available_copies when a book is issued
CREATE OR REPLACE FUNCTION trg_issue_book_fn()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    UPDATE Books
    SET available_copies = available_copies - 1
    WHERE book_id = NEW.book_id;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE TRIGGER trg_issue_book
AFTER INSERT ON Issues
FOR EACH ROW EXECUTE FUNCTION trg_issue_book_fn();

-- Increase available_copies when a book is returned
CREATE OR REPLACE FUNCTION trg_return_book_fn()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.return_date IS NULL AND NEW.return_date IS NOT NULL THEN
        UPDATE Books
        SET available_copies = available_copies + 1
        WHERE book_id = NEW.book_id;
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE TRIGGER trg_return_book
AFTER UPDATE ON Issues
FOR EACH ROW EXECUTE FUNCTION trg_return_book_fn();
