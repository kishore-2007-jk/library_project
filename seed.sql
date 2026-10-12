-- PostgreSQL seed data (migrated from MySQL)
-- Run AFTER schema.sql

INSERT INTO Authors (name) VALUES
('George Orwell'), ('J.K. Rowling'), ('A.P.J. Abdul Kalam'),
('Chetan Bhagat'), ('R.K. Narayan'), ('Paulo Coelho');

INSERT INTO Categories (name) VALUES
('Fiction'), ('Fantasy'), ('Biography'), ('Self-Help');

INSERT INTO Members (name, email, phone, join_date) VALUES
('Arjun Kumar',   'arjun@example.com',   '9000000001', '2026-06-01'),
('Priya Sharma',  'priya@example.com',   '9000000002', '2026-06-10'),
('Karthik Raj',   'karthik@example.com', '9000000003', '2026-07-05'),
('Divya Lakshmi', 'divya@example.com',   '9000000004', '2026-07-20'),
('Rahul Menon',   'rahul@example.com',   '9000000005', '2026-08-15');

-- Temporarily disable trigger so seed inserts don't double-decrement copies
ALTER TABLE Issues DISABLE TRIGGER trg_issue_book;

INSERT INTO Books (title, author_id, category_id, isbn, total_copies, available_copies) VALUES
('1984',                                      1, 1, 'ISBN-1001', 3, 2),
('Animal Farm',                               1, 1, 'ISBN-1002', 2, 2),
('Harry Potter and the Philosopher''s Stone', 2, 2, 'ISBN-1003', 4, 3),
('Wings of Fire',                             3, 3, 'ISBN-1004', 3, 2),
('Five Point Someone',                        4, 1, 'ISBN-1005', 2, 2),
('Malgudi Days',                              5, 1, 'ISBN-1006', 3, 3),
('The Alchemist',                             6, 1, 'ISBN-1007', 2, 2),
('Ignited Minds',                             3, 4, 'ISBN-1008', 2, 2);

INSERT INTO Issues (book_id, member_id, issue_date, due_date, return_date) VALUES
(1, 1, '2026-09-01', '2026-09-15', NULL),
(3, 2, '2026-09-28', '2026-10-12', NULL),
(4, 3, '2026-09-18', '2026-10-02', NULL),
(5, 1, '2026-09-10', '2026-09-24', '2026-09-22'),
(2, 4, '2026-08-20', '2026-09-03', '2026-09-10');

ALTER TABLE Issues ENABLE TRIGGER trg_issue_book;

INSERT INTO Fines (issue_id, amount, paid) VALUES (5, 14.00, FALSE);
