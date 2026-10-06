import sys, os, shutil
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')
os.makedirs('uploads', exist_ok=True)
shutil.copy('../Personal_Finance_Dataset.csv', 'uploads/Personal_Finance_Dataset.csv')

from app import load_and_validate, answer_question, compute_summary, compute_category, compute_monthly, generate_insights, generate_suggestions, compute_top_expenses
import re

df, err = load_and_validate('uploads/Personal_Finance_Dataset.csv')
assert err is None, f"Load failed: {err}"

# --- Summary checks
summary = compute_summary(df)
assert summary['total_transactions'] == 1500
assert summary['expense_count'] == 1222
assert summary['income_count'] == 278
print("PASS: summary counts correct")

# --- Category checks
cat = compute_category(df)
assert cat['category_labels'][0] == 'Travel', f"Expected Travel, got {cat['category_labels'][0]}"
assert len(cat['category_labels']) == 8   # Investment/Other are Income-only
print(f"PASS: top category = {cat['category_labels'][0]}, {len(cat['category_labels'])} expense categories")

# --- Monthly checks
monthly = compute_monthly(df)
assert len(monthly['monthly_labels']) == 60, f"Expected 60 months, got {len(monthly['monthly_labels'])}"
print(f"PASS: monthly data has {len(monthly['monthly_labels'])} months (Jan 2020 to Dec 2024)")

# --- Top 10 checks
top = compute_top_expenses(df, 10)
assert len(top) == 10
print(f"PASS: top 10 expenses, highest = ${top[0]['Amount']}")

# --- Insights
insights = generate_insights(df, summary, cat, monthly)
assert len(insights) >= 6
print(f"PASS: {len(insights)} insights generated")

# --- Suggestions
suggestions = generate_suggestions(df, cat)
assert len(suggestions) >= 3
print(f"PASS: {len(suggestions)} suggestions generated")

# --- Q&A
print("\n--- Q&A TESTS ---")
tests = [
    ("How much did I spend?",                    "$1,227,194.37"),
    ("Which category did I spend the most on?",  "Travel"),
    ("What was my largest expense?",             "$1,999.82"),
    ("How much did I spend on rent?",            "Rent"),
    ("What month had the highest spending?",     None),   # just check no crash
    ("What was my net balance?",                 "deficit"),
    ("How many transactions are there?",         "1500"),
    ("What happened in 2022?",                   "2022"),
    ("What categories do I have?",               "Travel"),
    ("What is my average transaction?",          "$1,004.25"),
]
for q, expected in tests:
    ans = answer_question(q, df)
    if expected:
        assert expected.lower() in ans.lower(), f"Q: '{q}'\nA: '{ans}'\nExpected to contain: '{expected}'"
    print(f"  PASS  Q: {q}")
    print(f"        A: {ans}")

print("\nALL TESTS PASSED")
