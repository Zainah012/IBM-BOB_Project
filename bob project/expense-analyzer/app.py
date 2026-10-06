"""
AI Personal Expense Analyzer
------------------------------
Flask web application that reads a personal finance CSV, performs
full data analysis, and serves results via a clean web interface.

Dataset columns expected:
    Date | Transaction Description | Category | Amount | Type

Type values observed in dataset: "Expense", "Income"

Author : [Your Name]
Project: AI/ML Internship Project
"""

import os
import re
import json
import numpy as np
import pandas as pd
from flask import Flask, render_template, request, jsonify, session
from werkzeug.utils import secure_filename

# ─── App Configuration ────────────────────────────────────────────────────────

app = Flask(__name__)
app.secret_key = "expense-analyzer-secret-key"   # Change in production

UPLOAD_FOLDER    = os.path.join(os.path.dirname(__file__), "uploads")
ALLOWED_EXTENSIONS = {"csv"}
REQUIRED_COLUMNS   = {"Date", "Transaction Description", "Category", "Amount", "Type"}

app.config["UPLOAD_FOLDER"]      = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024   # 10 MB

# ─── Helpers ──────────────────────────────────────────────────────────────────

def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def fmt_currency(value: float) -> str:
    """Format a float as a dollar currency string."""
    return f"${value:,.2f}"


def load_and_validate(filepath: str):
    """
    Load the CSV, validate columns, parse dates and amounts.
    Returns (df, error_string).  error_string is None on success.
    """
    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        return None, f"Could not read CSV file: {e}"

    if df.empty:
        return None, "The uploaded CSV file is empty."

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        return None, f"Missing required columns: {', '.join(sorted(missing))}"

    # Parse dates — coerce bad values to NaT
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    bad_dates = df["Date"].isna().sum()
    if bad_dates == len(df):
        return None, "No valid dates found in the Date column."
    if bad_dates > 0:
        df = df.dropna(subset=["Date"])

    # Parse amounts — coerce bad values to NaN
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce")
    bad_amounts = df["Amount"].isna().sum()
    if bad_amounts > 0:
        df = df.dropna(subset=["Amount"])

    if df.empty:
        return None, "No valid rows remain after cleaning the data."

    # Derived columns
    df["Month"]     = df["Date"].dt.to_period("M").astype(str)   # e.g. "2020-01"
    df["MonthLabel"] = df["Date"].dt.strftime("%b %Y")            # e.g. "Jan 2020"
    df["Year"]      = df["Date"].dt.year

    return df, None


# ─── Analysis Engine ──────────────────────────────────────────────────────────

def compute_summary(df: pd.DataFrame) -> dict:
    """Top-level numeric summary, split by Type where meaningful."""
    expenses_df = df[df["Type"] == "Expense"]
    income_df   = df[df["Type"] == "Income"]

    total_rows        = len(df)
    total_expenses    = expenses_df["Amount"].sum()
    total_income      = income_df["Amount"].sum()
    avg_amount        = df["Amount"].mean()
    highest_expense   = expenses_df["Amount"].max() if not expenses_df.empty else 0
    lowest_expense    = expenses_df["Amount"].min() if not expenses_df.empty else 0
    date_min          = df["Date"].min().strftime("%d %b %Y")
    date_max          = df["Date"].max().strftime("%d %b %Y")
    top_cat           = (
        expenses_df.groupby("Category")["Amount"].sum().idxmax()
        if not expenses_df.empty else "N/A"
    )
    expense_count     = len(expenses_df)
    income_count      = len(income_df)

    return {
        "total_expenses":      fmt_currency(total_expenses),
        "total_income":        fmt_currency(total_income),
        "total_transactions":  total_rows,
        "expense_count":       expense_count,
        "income_count":        income_count,
        "avg_transaction":     fmt_currency(avg_amount),
        "highest_expense":     fmt_currency(highest_expense),
        "lowest_expense":      fmt_currency(lowest_expense),
        "date_range":          f"{date_min} – {date_max}",
        "top_category":        top_cat,
    }


def compute_category(df: pd.DataFrame) -> dict:
    """Category-wise totals and counts (expenses only)."""
    expenses_df = df[df["Type"] == "Expense"]
    grp = (
        expenses_df.groupby("Category")["Amount"]
        .agg(total="sum", count="count")
        .sort_values("total", ascending=False)
        .reset_index()
    )
    return {
        "category_labels": grp["Category"].tolist(),
        "category_values": grp["total"].round(2).tolist(),
        "category_counts": grp["count"].tolist(),
    }


def compute_monthly(df: pd.DataFrame) -> dict:
    """Month-by-month expense totals in chronological order."""
    expenses_df = df[df["Type"] == "Expense"].copy()
    grp = (
        expenses_df.groupby("Month")["Amount"]
        .sum()
        .reset_index()
        .sort_values("Month")
    )
    # Build readable labels (Jan 2020 …) from the period string
    grp["Label"] = pd.to_datetime(grp["Month"]).dt.strftime("%b %Y")
    return {
        "monthly_labels": grp["Label"].tolist(),
        "monthly_values": grp["Amount"].round(2).tolist(),
    }


def compute_top_expenses(df: pd.DataFrame, n: int = 10) -> list:
    """Top-n individual expense transactions by amount."""
    expenses_df = df[df["Type"] == "Expense"].copy()
    top = expenses_df.nlargest(n, "Amount")[
        ["Date", "Transaction Description", "Category", "Amount", "Type"]
    ].copy()
    top["Date"] = top["Date"].dt.strftime("%d %b %Y")
    top["Amount"] = top["Amount"].round(2)
    return top.to_dict(orient="records")


def compute_charts_top_categories(df: pd.DataFrame, n: int = 8) -> dict:
    """Top-n expense categories for the horizontal bar chart."""
    cat = compute_category(df)
    return {
        "top_expense_labels": cat["category_labels"][:n],
        "top_expense_values": cat["category_values"][:n],
    }


def generate_insights(df: pd.DataFrame, summary: dict, cat: dict, monthly: dict) -> list:
    """
    Rule-based insights derived entirely from the real dataset.
    Each insight is a dict with 'icon' and 'text'.
    """
    insights = []
    expenses_df = df[df["Type"] == "Expense"]

    # 1. Top spending category
    if cat["category_labels"]:
        top_cat   = cat["category_labels"][0]
        top_val   = cat["category_values"][0]
        total_exp = expenses_df["Amount"].sum()
        pct       = (top_val / total_exp * 100) if total_exp else 0
        insights.append({
            "icon": "🏆",
            "text": (
                f"Your highest spending category is <strong>{top_cat}</strong>, "
                f"accounting for {fmt_currency(top_val)} ({pct:.1f}% of total expenses)."
            )
        })

    # 2. Largest single transaction
    if not expenses_df.empty:
        row = expenses_df.loc[expenses_df["Amount"].idxmax()]
        insights.append({
            "icon": "💸",
            "text": (
                f"Your largest single expense was {fmt_currency(row['Amount'])} "
                f"on <strong>{row['Date'].strftime('%d %b %Y')}</strong> "
                f"({row['Category']} — {row['Transaction Description']})."
            )
        })

    # 3. Highest spending month
    if monthly["monthly_labels"]:
        max_idx   = int(np.argmax(monthly["monthly_values"]))
        max_month = monthly["monthly_labels"][max_idx]
        max_val   = monthly["monthly_values"][max_idx]
        insights.append({
            "icon": "📅",
            "text": (
                f"<strong>{max_month}</strong> was your highest-spending month "
                f"with {fmt_currency(max_val)} in expenses."
            )
        })

    # 4. Lowest spending month
    if monthly["monthly_labels"]:
        min_idx   = int(np.argmin(monthly["monthly_values"]))
        min_month = monthly["monthly_labels"][min_idx]
        min_val   = monthly["monthly_values"][min_idx]
        insights.append({
            "icon": "📉",
            "text": (
                f"<strong>{min_month}</strong> was your lowest-spending month "
                f"with {fmt_currency(min_val)} in expenses."
            )
        })

    # 5. Unusually high transactions (> mean + 2 * std)
    mean_amt = expenses_df["Amount"].mean()
    std_amt  = expenses_df["Amount"].std()
    threshold = mean_amt + 2 * std_amt
    outliers  = expenses_df[expenses_df["Amount"] > threshold]
    if not outliers.empty:
        insights.append({
            "icon": "⚠️",
            "text": (
                f"There are <strong>{len(outliers)} unusually high transactions</strong> "
                f"above {fmt_currency(threshold)} (mean + 2× std dev). "
                f"These may be worth reviewing."
            )
        })

    # 6. Income vs Expense balance
    total_income  = df[df["Type"] == "Income"]["Amount"].sum()
    total_expense = expenses_df["Amount"].sum()
    if total_income > 0:
        balance = total_income - total_expense
        label   = "surplus" if balance >= 0 else "deficit"
        insights.append({
            "icon": "⚖️",
            "text": (
                f"Total income is {fmt_currency(total_income)} vs total expenses "
                f"of {fmt_currency(total_expense)}, resulting in a "
                f"<strong>{label} of {fmt_currency(abs(balance))}</strong>."
            )
        })

    # 7. Year-over-year trend (if multiple years)
    yearly = expenses_df.groupby("Year")["Amount"].sum().sort_index()
    if len(yearly) >= 2:
        first_yr, first_val = yearly.index[0],  yearly.iloc[0]
        last_yr,  last_val  = yearly.index[-1], yearly.iloc[-1]
        change_pct = ((last_val - first_val) / first_val * 100) if first_val else 0
        direction  = "increased" if change_pct >= 0 else "decreased"
        insights.append({
            "icon": "📈",
            "text": (
                f"Expenses <strong>{direction} by {abs(change_pct):.1f}%</strong> "
                f"from {first_yr} ({fmt_currency(first_val)}) "
                f"to {last_yr} ({fmt_currency(last_val)})."
            )
        })

    return insights


def generate_suggestions(df: pd.DataFrame, cat: dict) -> list:
    """
    Data-driven spending suggestions.
    Clearly labelled as general suggestions, not financial advice.
    """
    suggestions = []
    expenses_df = df[df["Type"] == "Expense"]
    total_exp   = expenses_df["Amount"].sum()

    # Suggestion per top-3 categories
    for i, (label, value) in enumerate(zip(cat["category_labels"][:3], cat["category_values"][:3])):
        pct = (value / total_exp * 100) if total_exp else 0
        suggestions.append({
            "icon": ["🍽️", "🛍️", "🏠"][i] if i < 3 else "💡",
            "text": (
                f"<strong>{label}</strong> represents {pct:.1f}% of your expenses "
                f"({fmt_currency(value)}). Consider reviewing this category for "
                f"potential savings opportunities."
            )
        })

    # Budgeting suggestion based on avg monthly spend
    monthly_vals = expenses_df.groupby("Month")["Amount"].sum()
    if not monthly_vals.empty:
        avg_monthly = monthly_vals.mean()
        suggestions.append({
            "icon": "📋",
            "text": (
                f"Your average monthly spending is {fmt_currency(avg_monthly)}. "
                f"Setting a monthly budget around this figure can help you track "
                f"and manage your finances more effectively."
            )
        })

    # Outlier suggestion
    mean_amt  = expenses_df["Amount"].mean()
    std_amt   = expenses_df["Amount"].std()
    threshold = mean_amt + 2 * std_amt
    outlier_count = (expenses_df["Amount"] > threshold).sum()
    if outlier_count > 0:
        suggestions.append({
            "icon": "🔍",
            "text": (
                f"You have {outlier_count} transaction(s) significantly above your "
                f"average spend. Reviewing large one-off expenses can reveal areas "
                f"where costs can be reduced."
            )
        })

    # Income vs expense
    total_income = df[df["Type"] == "Income"]["Amount"].sum()
    if total_income > 0 and total_exp > total_income:
        suggestions.append({
            "icon": "💡",
            "text": (
                "Your total expenses exceed your recorded income. "
                "Tracking all income sources and reducing discretionary spending "
                "may help improve your financial balance."
            )
        })

    # General disclaimer
    suggestions.append({
        "icon": "ℹ️",
        "text": (
            "<em>These are general suggestions based on patterns in your data — "
            "not professional financial advice. Please consult a financial advisor "
            "for personalised guidance.</em>"
        )
    })

    return suggestions


# ─── Q&A Engine ───────────────────────────────────────────────────────────────

def answer_question(question: str, df: pd.DataFrame) -> str:
    """
    Keyword-based Q&A over the real dataset.
    Returns a plain-text answer string.
    """
    q = question.lower().strip()
    expenses_df = df[df["Type"] == "Expense"]
    income_df   = df[df["Type"] == "Income"]

    # ── total expenses ──────────────────────────────────────
    if re.search(r"how much.*(spend|spent|expense|cost)", q) and \
       not re.search(r"categor|month|year|food|rent|travel|shop|health|entertain|util|invest|salary", q):
        total = expenses_df["Amount"].sum()
        return f"Your total expenses are {fmt_currency(total)} across {len(expenses_df)} transactions."

    # ── total income ─────────────────────────────────────────
    if re.search(r"(total|how much).*(income|earn|receiv)", q) or re.search(r"(income|earn|receiv).*(total|how much)", q):
        total = income_df["Amount"].sum()
        return f"Your total recorded income is {fmt_currency(total)} across {len(income_df)} transactions."

    # ── balance / net ─────────────────────────────────────────
    if re.search(r"balance|net|surplus|deficit|left over|save", q):
        total_exp = expenses_df["Amount"].sum()
        total_inc = income_df["Amount"].sum()
        balance   = total_inc - total_exp
        label     = "surplus" if balance >= 0 else "deficit"
        return (
            f"Total income: {fmt_currency(total_inc)} | "
            f"Total expenses: {fmt_currency(total_exp)} | "
            f"Net {label}: {fmt_currency(abs(balance))}."
        )

    # ── highest spending month (must come before generic category/spend check) ──
    if re.search(r"(highest|most|top|biggest).*(month|monthly)", q) or \
       re.search(r"month.*(highest|most|top)", q):
        monthly = expenses_df.groupby("Month")["Amount"].sum()
        top_month_key = monthly.idxmax()
        top_val       = monthly.max()
        label         = pd.to_datetime(top_month_key).strftime("%B %Y")
        return f"Your highest-spending month was {label} with {fmt_currency(top_val)} in expenses."

    # ── top / highest spending category ──────────────────────
    if re.search(r"(top|most|highest|biggest).*(categor|spend|spent)", q) or \
       re.search(r"categor.*(most|highest|top|spent)", q):
        grp = expenses_df.groupby("Category")["Amount"].sum().sort_values(ascending=False)
        top_cat = grp.index[0]
        top_val = grp.iloc[0]
        return (
            f"Your highest spending category is '{top_cat}' with "
            f"{fmt_currency(top_val)} in total expenses."
        )

    # ── specific category spend ───────────────────────────────
    categories = df["Category"].unique()
    for cat in categories:
        if cat.lower() in q:
            cat_df = expenses_df[expenses_df["Category"] == cat]
            if cat_df.empty:
                return f"No expense transactions found for the '{cat}' category."
            total = cat_df["Amount"].sum()
            count = len(cat_df)
            avg   = cat_df["Amount"].mean()
            return (
                f"You spent {fmt_currency(total)} on '{cat}' across "
                f"{count} transactions (average {fmt_currency(avg)} per transaction)."
            )

    # ── largest / biggest expense ─────────────────────────────
    if re.search(r"largest|biggest|highest|maximum|most expensive", q) and \
       re.search(r"expense|transaction|purchase|spent", q):
        row = expenses_df.loc[expenses_df["Amount"].idxmax()]
        return (
            f"Your largest expense was {fmt_currency(row['Amount'])} on "
            f"{row['Date'].strftime('%d %b %Y')} — "
            f"'{row['Transaction Description']}' ({row['Category']})."
        )

    # ── smallest expense ──────────────────────────────────────
    if re.search(r"smallest|lowest|minimum|cheapest|least", q) and \
       re.search(r"expense|transaction|purchase|spent", q):
        row = expenses_df.loc[expenses_df["Amount"].idxmin()]
        return (
            f"Your smallest expense was {fmt_currency(row['Amount'])} on "
            f"{row['Date'].strftime('%d %b %Y')} — "
            f"'{row['Transaction Description']}' ({row['Category']})."
        )

    # ── lowest spending month ─────────────────────────────────
    if re.search(r"(lowest|least|minimum).*(month|monthly)", q) or \
       re.search(r"month.*(lowest|least|minimum)", q):
        monthly = expenses_df.groupby("Month")["Amount"].sum()
        low_month_key = monthly.idxmin()
        low_val       = monthly.min()
        label         = pd.to_datetime(low_month_key).strftime("%B %Y")
        return f"Your lowest-spending month was {label} with {fmt_currency(low_val)} in expenses."

    # ── average transaction ───────────────────────────────────
    if re.search(r"average|mean|typical", q) and \
       re.search(r"spend|spent|transaction|expense", q):
        avg_exp = expenses_df["Amount"].mean()
        avg_all = df["Amount"].mean()
        return (
            f"Your average expense transaction is {fmt_currency(avg_exp)}. "
            f"Average across all records (including income) is {fmt_currency(avg_all)}."
        )

    # ── number of transactions ────────────────────────────────
    if re.search(r"how many|number of|count|total.*(transaction|record|entry)", q):
        return (
            f"The dataset contains {len(df)} total records: "
            f"{len(expenses_df)} expense transactions and "
            f"{len(income_df)} income transactions."
        )

    # ── date range ────────────────────────────────────────────
    if re.search(r"date|period|range|when|how long|duration|start|end", q):
        d_min = df["Date"].min().strftime("%d %b %Y")
        d_max = df["Date"].max().strftime("%d %b %Y")
        return f"The dataset covers transactions from {d_min} to {d_max}."

    # ── categories list ───────────────────────────────────────
    if re.search(r"(what|list|show|which).*(categor)", q):
        cats = expenses_df["Category"].unique().tolist()
        return "Expense categories in your data: " + ", ".join(sorted(cats)) + "."

    # ── year spending ─────────────────────────────────────────
    year_match = re.search(r"\b(20\d{2})\b", q)
    if year_match:
        yr     = int(year_match.group(1))
        yr_df  = expenses_df[expenses_df["Year"] == yr]
        if yr_df.empty:
            return f"No expense data found for the year {yr}."
        total = yr_df["Amount"].sum()
        count = len(yr_df)
        return f"In {yr}, you had {count} expense transactions totalling {fmt_currency(total)}."

    # ── fallback ──────────────────────────────────────────────
    return (
        "I couldn't find a clear answer to that question in the available dataset. "
        "Try asking about: total expenses, a specific category (e.g. 'food', 'rent'), "
        "largest/smallest expense, highest/lowest spending month, income, or date range."
    )


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload_file():
    """Validate and save the uploaded CSV; store its path in the session."""
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request."}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "No file selected."}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Only CSV files are allowed."}), 400

    filename  = secure_filename(file.filename)
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(save_path)

    # Quick structural validation before confirming success
    _, err = load_and_validate(save_path)
    if err:
        os.remove(save_path)
        return jsonify({"error": err}), 400

    session["uploaded_file"] = save_path

    return jsonify({"message": "File uploaded successfully.", "filename": filename}), 200


@app.route("/analyze", methods=["POST"])
def analyze():
    """
    Full analysis pipeline.
    Returns summary, chart data, insights, suggestions, and top-10 table.
    """
    filepath = session.get("uploaded_file")
    if not filepath or not os.path.exists(filepath):
        return jsonify({"error": "No CSV file found. Please upload a file first."}), 400

    df, err = load_and_validate(filepath)
    if err:
        return jsonify({"error": err}), 400

    # Run all analysis functions
    summary     = compute_summary(df)
    cat         = compute_category(df)
    monthly     = compute_monthly(df)
    top_exp     = compute_top_expenses(df, n=10)
    top_cats    = compute_charts_top_categories(df)
    insights    = generate_insights(df, summary, cat, monthly)
    suggestions = generate_suggestions(df, cat)

    # Merge chart data into one object
    charts = {**cat, **monthly, **top_cats}

    return jsonify({
        "summary":      summary,
        "charts":       charts,
        "top_expenses": top_exp,
        "insights":     insights,
        "suggestions":  suggestions,
    }), 200


@app.route("/ask", methods=["POST"])
def ask():
    """Answer a natural-language question about the uploaded dataset."""
    filepath = session.get("uploaded_file")
    if not filepath or not os.path.exists(filepath):
        return jsonify({"error": "No CSV file found. Please upload and analyze a file first."}), 400

    data     = request.get_json()
    question = (data or {}).get("question", "").strip()
    if not question:
        return jsonify({"error": "Please enter a question."}), 400

    df, err = load_and_validate(filepath)
    if err:
        return jsonify({"error": err}), 400

    answer = answer_question(question, df)
    return jsonify({"answer": answer}), 200


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True, port=5000)
