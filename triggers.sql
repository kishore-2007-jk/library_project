-- Library Management System - triggers (PostgreSQL / Supabase)
-- Run AFTER schema.sql and seed.sql. Safe to re-run.

CREATE OR REPLACE FUNCTION fn_issue_book()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE books
    SET available_copies = available_copies - 1
    WHERE book_id = NEW.book_id;
    RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS trg_issue_book ON issues;
CREATE TRIGGER trg_issue_book
AFTER INSERT ON issues
FOR EACH ROW EXECUTE FUNCTION fn_issue_book();

CREATE OR REPLACE FUNCTION fn_return_book()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF OLD.return_date IS NULL AND NEW.return_date IS NOT NULL THEN
        UPDATE books
        SET available_copies = available_copies + 1
        WHERE book_id = NEW.book_id;
    END IF;
    RETURN NULL;
END;
$$;

DROP TRIGGER IF EXISTS trg_return_book ON issues;
CREATE TRIGGER trg_return_book
AFTER UPDATE ON issues
FOR EACH ROW EXECUTE FUNCTION fn_return_book();