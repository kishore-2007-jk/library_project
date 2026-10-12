const $ = id => document.getElementById(id);

// Escape text so data can't inject HTML into the page
const esc = s => String(s ?? "").replace(/[&<>"']/g,
  c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

// Talk to the Flask routes
async function api(url, method = "GET", body) {
  const res = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Something went wrong");
  return data;
}

function showMessage(text, isError = false) {
  const box = $("message");
  box.textContent = text;
  box.className = isError ? "err" : "ok";
  setTimeout(() => (box.className = ""), 4000);
}

// Fill a table body from a list of rows. A column is a field name or a function.
function fillTable(tableId, rows, cols) {
  const body = $(tableId).querySelector("tbody");
  if (!rows.length) {
    body.innerHTML = `<tr><td colspan="${cols.length}">No records</td></tr>`;
    return;
  }
  body.innerHTML = rows.map(r =>
    "<tr>" + cols.map(c => `<td>${typeof c === "function" ? c(r) : esc(r[c])}</td>`).join("") + "</tr>"
  ).join("");
}

// ---------- Loaders ----------
async function loadDashboard() {
  const d = await api("/api/dashboard");
  $("c-titles").textContent = d.total_titles;
  $("c-members").textContent = d.members;
  $("c-issued").textContent = d.currently_issued;
  $("c-overdue").textContent = d.overdue;

  const popular = await api("/api/popular");
  fillTable("popular-table", popular, ["title", "author", "times_issued"]);
}
async function loadBooks() {
  const q = encodeURIComponent($("search").value);
  const rows = await api("/api/books?search=" + q);
  fillTable("books-table", rows,
    ["book_id", "title", "author", "category",
     r => r.available_copies > 0
       ? `<span class="badge green">${r.available_copies} of ${r.total_copies} available</span>`
       : `<span class="badge red">All issued</span>`]);
}

async function loadMembers() {
  const rows = await api("/api/members");
  fillTable("members-table", rows, ["member_id", "name", "email", "phone", "join_date"]);
}

async function loadCirculation() {
  const books = await api("/api/books");
  const members = await api("/api/members");
  $("issue-book").innerHTML = '<option value="">Select book</option>' +
    books.filter(b => b.available_copies > 0)
         .map(b => `<option value="${b.book_id}">${esc(b.title)} (${b.available_copies} left)</option>`).join("");
  $("issue-member").innerHTML = '<option value="">Select member</option>' +
    members.map(m => `<option value="${m.member_id}">${esc(m.name)}</option>`).join("");

  const issued = await api("/api/issued");
  fillTable("issued-table", issued,
    ["issue_id", "title", "member", "issue_date", "due_date",
     r => `<button class="return-btn" onclick="returnBook(${r.issue_id})">Return</button> ` +
          (r.renewed
            ? "Renewed"
            : `<button class="return-btn" onclick="renewBook(${r.issue_id})">Renew +7 days</button>`)]);
}
// Builds a WhatsApp link with a ready-made reminder message
function remindBtn(r, text) {
  const phone = String(r.phone || "").replace(/\D/g, "");
  if (!phone) return "No phone";
  const url = `https://wa.me/91${phone}?text=${encodeURIComponent(text)}`;
  return `<a class="return-btn" target="_blank" href="${url}">Send WhatsApp</a>`;
}

async function loadOverdue() {
  const soon = await api("/api/due_soon");
  fillTable("duesoon-table", soon,
    ["member", "title", "due_date",
     r => `<span class="badge amber">${r.days_left} day(s) left</span>`,
     r => remindBtn(r, `Hello ${r.member}, your library book "${r.title}" is due on ${r.due_date}. Please return or renew it on time.`)]);

  const overdue = await api("/api/overdue");
  fillTable("overdue-table", overdue,
    ["member", "title", "due_date",
     r => `<span class="badge red">${r.days_overdue} days late</span>`,
     r => `₹${r.fine_so_far}`,
     r => remindBtn(r, `Hello ${r.member}, your library book "${r.title}" was due on ${r.due_date} and is ${r.days_overdue} days overdue. Fine so far: Rs ${r.fine_so_far}. Please return it soon.`)]);

  const fines = await api("/api/fines");
  fillTable("fines-table", fines,
    ["member", "title", r => `₹${r.amount}`,
     r => r.paid
       ? `<span class="badge green">Paid</span>`
       : `<span class="badge red">Unpaid</span> <button class="return-btn" onclick="payFine(${r.fine_id})">Mark as Paid</button>`]);
}

const loaders = {
  dashboard: loadDashboard,
  books: loadBooks,
  members: loadMembers,
  circulation: loadCirculation,
  overdue: loadOverdue,
};

// ---------- Tabs ----------
document.querySelectorAll("nav button").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll("nav button").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
    btn.classList.add("active");
    $(btn.dataset.tab).classList.add("active");
    loaders[btn.dataset.tab]().catch(e => showMessage(e.message, true));
  });
});

// ---------- Actions ----------
$("search").addEventListener("input", () => loadBooks().catch(e => showMessage(e.message, true)));

$("member-form").addEventListener("submit", async e => {
  e.preventDefault();
  try {
    const r = await api("/api/members", "POST", {
      name: $("m-name").value,
      email: $("m-email").value,
      phone: $("m-phone").value,
    });
    showMessage(r.message);
    e.target.reset();
    loadMembers();
  } catch (err) { showMessage(err.message, true); }
});

$("issue-form").addEventListener("submit", async e => {
  e.preventDefault();
  try {
    const r = await api("/api/issue", "POST", {
      book_id: $("issue-book").value,
      member_id: $("issue-member").value,
    });
    showMessage(r.message);
    loadCirculation();
  } catch (err) { showMessage(err.message, true); }
});

async function returnBook(issueId) {
  try {
    const r = await api("/api/return", "POST", { issue_id: issueId });
    showMessage(r.fine > 0 ? `Book returned. Fine: ₹${r.fine}` : "Book returned. No fine.");
    loadCirculation();
  } catch (err) { showMessage(err.message, true); }
}
async function payFine(fineId) {
  try {
    const r = await api("/api/pay_fine", "POST", { fine_id: fineId });
    showMessage(r.message);
    loadOverdue();
  } catch (err) { showMessage(err.message, true); }
}
async function renewBook(issueId) {
  try {
    const r = await api("/api/renew", "POST", { issue_id: issueId });
    showMessage(r.message);
    loadCirculation();
  } catch (err) { showMessage(err.message, true); }
}
// First page load
loadDashboard().catch(e => showMessage(e.message, true));
