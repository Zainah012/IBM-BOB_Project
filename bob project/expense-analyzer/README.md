# AI Personal Expense Analyzer

A Flask web application that analyzes personal expense CSV data and provides spending summaries, category breakdowns, monthly trend visualizations, automated insights, spending suggestions, and a natural-language Q&A interface.

Built as an academic AI/ML internship project.

---

## Features

| # | Feature |
|---|---------|
| 1 | Upload a personal expense CSV file |
| 2 | Expense summary (totals, income, averages, date range) |
| 3 | Category-wise spending analysis |
| 4 | Monthly spending trend analysis |
| 5 | Top 10 highest expense transactions table |
| 6 | Interactive charts (doughnut, bar, horizontal bar) via Chart.js |
| 7 | Automated spending insights based on analyzed data |
| 8 | Natural-language Q&A about the uploaded dataset |
| 9 | Data-based spending management suggestions |
| 10 | Responsive, clean web interface |

---

## Project Structure

```
expense-analyzer/
├── app.py                  # Flask application, analysis engine, API routes
├── requirements.txt        # Python dependencies
├── README.md               # This file
├── .gitignore              # Ignores uploads/, __pycache__, etc.
├── uploads/                # Uploaded CSV files (git-ignored)
├── templates/
│   └── index.html          # Main UI (upload → summary → charts → Q&A)
└── static/
    ├── css/
    │   └── style.css       # Application styles
    └── js/
        └── main.js         # Frontend logic and Chart.js rendering
```

---

## Dataset

The application was developed and tested against a personal finance dataset with the following structure:

| Column | Description |
|--------|-------------|
| `Date` | Transaction date (YYYY-MM-DD) |
| `Transaction Description` | Description of the transaction |
| `Category` | Spending category (e.g. Food & Drink, Rent, Travel) |
| `Amount` | Transaction amount (numeric) |
| `Type` | `Expense` or `Income` |

- **1,500 rows** of transaction records
- **Date range:** January 2020 – December 2024
- **Expense categories:** Travel, Rent, Food & Drink, Salary, Entertainment, Shopping, Utilities, Health & Fitness

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, Flask |
| Data analysis | pandas, NumPy |
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| Visualizations | Chart.js |

---

## Getting Started

### 1. Install dependencies

```bash
cd expense-analyzer
pip install -r requirements.txt
```

### 2. Run the application

```powershell
cd expense-analyzer
python app.py
```

Open your browser at **http://localhost:5000**

### 3. Use the application

1. Click **Browse File** or drag and drop your expense CSV
2. Click **Analyze My Expenses**
3. View the summary cards, charts, top-10 table, insights, and suggestions
4. Ask questions in the **Ask About Your Expenses** section

---

## Analysis Engine

All analysis is performed in Python using pandas and NumPy:

- **Summary** — total expenses, income, transaction counts, averages, date range
- **Categories** — spending grouped and ranked by category
- **Monthly trends** — month-by-month expense totals across the full date range
- **Top expenses** — 10 highest individual expense transactions
- **Insights** — rule-based patterns: top category, peak month, outlier transactions, income vs expense balance, year-over-year trend
- **Suggestions** — data-driven recommendations based on the analyzed figures
- **Q&A** — keyword-based answers using the real dataset values

---

## API Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| `GET` | `/` | Main application page |
| `POST` | `/upload` | Upload and validate a CSV file |
| `POST` | `/analyze` | Run full analysis and return results |
| `POST` | `/ask` | Answer a natural-language question |

---

## Testing

Run the integration test suite:

```powershell
cd expense-analyzer
python _test_http.py
```

---

*AI Personal Expense Analyzer — AI/ML Internship Project*
