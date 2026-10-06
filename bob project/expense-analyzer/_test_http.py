"""
Full integration test using Flask's built-in test client.
No network required — runs entirely in-process.
"""
import sys, os, io, json
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")
os.makedirs("uploads", exist_ok=True)

from app import app

client = app.test_client()
app.config["TESTING"] = True
app.secret_key = "test-secret"

CSV_PATH = os.path.join("..", "Personal_Finance_Dataset.csv")

print("=" * 60)
print("AI Personal Expense Analyzer — Integration Test")
print("=" * 60)

# ── 1. GET / ──────────────────────────────────────────────────
r = client.get("/")
assert r.status_code == 200, f"GET / returned {r.status_code}"
assert b"AI Personal Expense Analyzer" in r.data
print("PASS  GET /  ->  200 OK, page title found")

# ── 2. POST /upload (no file) ─────────────────────────────────
r = client.post("/upload", data={})
assert r.status_code == 400
print("PASS  POST /upload (no file)  ->  400 as expected")

# ── 3. POST /upload (wrong type) ──────────────────────────────
r = client.post("/upload",
                data={"file": (io.BytesIO(b"data"), "test.txt")},
                content_type="multipart/form-data")
assert r.status_code == 400
print("PASS  POST /upload (wrong extension)  ->  400 as expected")

# ── 4. POST /upload (CSV missing required columns) ────────────
r = client.post("/upload",
                data={"file": (io.BytesIO(b"col1,col2\n1,2\n3,4"), "bad.csv")},
                content_type="multipart/form-data")
assert r.status_code == 400
err = r.get_json()["error"]
assert "Missing required columns" in err, f"Unexpected error: {err}"
print(f"PASS  POST /upload (missing columns)  ->  400, '{err}'")

# ── 5. POST /upload (valid 1500-row CSV) ──────────────────────
with open(CSV_PATH, "rb") as f:
    csv_bytes = f.read()

r = client.post(
    "/upload",
    data={"file": (io.BytesIO(csv_bytes), "Personal_Finance_Dataset.csv")},
    content_type="multipart/form-data",
)
assert r.status_code == 200, f"Upload failed: {r.get_json()}"
assert r.get_json()["message"] == "File uploaded successfully."
print(f"PASS  POST /upload (1500-row CSV)  ->  uploaded successfully")

# ── 6. POST /analyze ──────────────────────────────────────────
r = client.post("/analyze")
assert r.status_code == 200, f"/analyze failed {r.status_code}: {r.get_json()}"
result = r.get_json()

for key in ("summary", "charts", "insights", "suggestions", "top_expenses"):
    assert key in result, f"Missing key: {key}"
print("PASS  POST /analyze  ->  all 5 sections present")

s = result["summary"]
c = result["charts"]

print()
print("  ── Summary ──────────────────────────────────────────")
print(f"  total_expenses      = {s['total_expenses']}")
print(f"  total_income        = {s['total_income']}")
print(f"  total_transactions  = {s['total_transactions']}")
print(f"  expense_count       = {s['expense_count']}")
print(f"  income_count        = {s['income_count']}")
print(f"  avg_transaction     = {s['avg_transaction']}")
print(f"  highest_expense     = {s['highest_expense']}")
print(f"  lowest_expense      = {s['lowest_expense']}")
print(f"  date_range          = {s['date_range']}")
print(f"  top_category        = {s['top_category']}")
print()
print("  ── Category analysis (all 8 expense categories) ─────")
for lbl, val, cnt in zip(c["category_labels"], c["category_values"], c["category_counts"]):
    print(f"  {lbl:<20} ${val:>12,.2f}   ({cnt} transactions)")
print()
print("  ── Monthly analysis (first 4 / last 4 months) ───────")
for lbl, val in zip(c["monthly_labels"][:4], c["monthly_values"][:4]):
    print(f"  {lbl}   ${val:>10,.2f}")
print("  ...")
for lbl, val in zip(c["monthly_labels"][-4:], c["monthly_values"][-4:]):
    print(f"  {lbl}   ${val:>10,.2f}")
print()
print("  ── Top 10 highest expense transactions ──────────────")
for i, row in enumerate(result["top_expenses"], 1):
    print(f"  {i:>2}. {row['Date']}  {row['Category']:<16}  ${row['Amount']:>8,.2f}  {row['Transaction Description'][:40]}")
print()
print("  ── Insights ─────────────────────────────────────────")
for ins in result["insights"]:
    clean = ins["text"].replace("<strong>","").replace("</strong>","").replace("<em>","").replace("</em>","")
    print(f"  {ins['icon']}  {clean[:90]}")
print()
print("  ── Suggestions ──────────────────────────────────────")
for sug in result["suggestions"]:
    clean = sug["text"].replace("<strong>","").replace("</strong>","").replace("<em>","").replace("</em>","")
    print(f"  {sug['icon']}  {clean[:90]}")

# Value assertions
assert s["total_transactions"] == 1500,        f"transactions: got {s['total_transactions']}"
assert s["expense_count"]      == 1222,        f"expenses: got {s['expense_count']}"
assert s["income_count"]       == 278,         f"income: got {s['income_count']}"
assert s["top_category"]       == "Travel",    f"top cat: got {s['top_category']}"
assert s["total_expenses"]     == "$1,227,194.37"
assert s["total_income"]       == "$734,087.00"
assert len(c["monthly_labels"])    == 60,      f"months: got {len(c['monthly_labels'])}"
assert len(c["category_labels"])   == 8,       f"categories: got {len(c['category_labels'])}"
assert c["category_labels"][0]     == "Travel"
assert len(result["top_expenses"]) == 10
assert result["top_expenses"][0]["Amount"] == 1999.82
assert len(result["insights"])     >= 6
assert len(result["suggestions"])  >= 3
print("PASS  All /analyze value assertions passed")

# ── 7. Q&A ────────────────────────────────────────────────────
print()
print("  ── Q&A Tests ────────────────────────────────────────")
qa_tests = [
    ("How much did I spend?",                   "$1,227,194.37"),
    ("Which category did I spend the most on?", "Travel"),
    ("What was my largest expense?",            "$1,999.82"),
    ("How much did I spend on rent?",           "$162,075.39"),
    ("What month had the highest spending?",    "August 2020"),
    ("What was my net balance?",                "deficit"),
    ("How many transactions are there?",        "1500"),
    ("What happened in 2022?",                  "250"),
    ("What categories do I have?",              "Travel"),
    ("What is my average transaction?",         "$1,004.25"),
]
for question, expected in qa_tests:
    r = client.post("/ask",
                    data=json.dumps({"question": question}),
                    content_type="application/json")
    assert r.status_code == 200, f"/ask returned {r.status_code}"
    answer = r.get_json()["answer"]
    assert expected.lower() in answer.lower(), (
        f"\n  Q: {question}\n  A: {answer}\n  Expected to contain: '{expected}'"
    )
    print(f"  PASS  Q: {question}")
    print(f"        A: {answer}")

# ── 8. Q&A error cases ────────────────────────────────────────
r = client.post("/ask",
                data=json.dumps({"question": ""}),
                content_type="application/json")
assert r.status_code == 400
print()
print("PASS  POST /ask (empty question)  ->  400 as expected")

print()
print("=" * 60)
print("ALL INTEGRATION TESTS PASSED")
print("=" * 60)
