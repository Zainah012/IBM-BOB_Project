/**
 * AI Personal Expense Analyzer — Frontend Logic
 * ------------------------------------------------
 * Handles file upload, triggers analysis, renders
 * summary cards, charts, top-10 table, insights,
 * suggestions, and the Q&A feature.
 */

// ── DOM References ──────────────────────────────────────────
const uploadArea      = document.getElementById("upload-area");
const fileInput       = document.getElementById("csv-file-input");
const browseBtn       = document.getElementById("browse-btn");
const uploadStatus    = document.getElementById("upload-status");
const statusMessage   = document.getElementById("status-message");
const uploadActions   = document.getElementById("upload-actions");
const analyzeBtn      = document.getElementById("analyze-btn");
const loading         = document.getElementById("loading");

const summarySection  = document.getElementById("summary-section");
const summaryGrid     = document.getElementById("summary-grid");
const chartsSection   = document.getElementById("charts-section");
const topTableSection = document.getElementById("top-table-section");
const topExpTbody     = document.getElementById("top-expense-tbody");
const insightsSection = document.getElementById("insights-section");
const insightsContent = document.getElementById("insights-content");
const suggestSection  = document.getElementById("suggestions-section");
const suggestContent  = document.getElementById("suggestions-content");
const qaSection       = document.getElementById("qa-section");
const qaInput         = document.getElementById("qa-input");
const qaSubmitBtn     = document.getElementById("qa-submit-btn");
const qaAnswer        = document.getElementById("qa-answer");
const qaAnswerText    = document.getElementById("qa-answer-text");

// All result sections (hidden until analysis completes)
const resultSections = [
  summarySection, chartsSection, topTableSection,
  insightsSection, suggestSection, qaSection
];

// Chart instances — kept so they can be destroyed on re-upload
let categoryChart, monthlyChart, topExpensesChart;

// ── Upload: click to browse ─────────────────────────────────
browseBtn.addEventListener("click", () => fileInput.click());
uploadArea.addEventListener("click", (e) => {
  if (e.target !== browseBtn) fileInput.click();
});

// ── Upload: drag & drop ─────────────────────────────────────
uploadArea.addEventListener("dragover", (e) => {
  e.preventDefault();
  uploadArea.classList.add("drag-over");
});
uploadArea.addEventListener("dragleave", () => uploadArea.classList.remove("drag-over"));
uploadArea.addEventListener("drop", (e) => {
  e.preventDefault();
  uploadArea.classList.remove("drag-over");
  const file = e.dataTransfer.files[0];
  if (file) handleFileSelected(file);
});

// ── Upload: file input change ───────────────────────────────
fileInput.addEventListener("change", () => {
  if (fileInput.files[0]) handleFileSelected(fileInput.files[0]);
});

/**
 * Validate and upload the selected CSV file to the server.
 * @param {File} file
 */
async function handleFileSelected(file) {
  if (!file.name.endsWith(".csv")) {
    showStatus("error", "❌ Only CSV files are supported.");
    return;
  }

  showStatus("", "⏳ Uploading…");
  uploadActions.classList.add("hidden");

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res  = await fetch("/upload", { method: "POST", body: formData });
    const data = await res.json();

    if (!res.ok) {
      showStatus("error", `❌ ${data.error}`);
      return;
    }

    showStatus("success", `✅ "${file.name}" uploaded successfully. Click Analyze to continue.`);
    uploadActions.classList.remove("hidden");
  } catch {
    showStatus("error", "❌ Upload failed. Please try again.");
  }
}

/** Display a status message below the upload area. */
function showStatus(type, message) {
  uploadStatus.className = `upload-status ${type}`;
  uploadStatus.classList.remove("hidden");
  statusMessage.textContent = message;
}

// ── Analyze Button ──────────────────────────────────────────
analyzeBtn.addEventListener("click", async () => {
  // Hide previous results
  resultSections.forEach(s => s.classList.add("hidden"));
  loading.classList.remove("hidden");
  analyzeBtn.disabled = true;

  try {
    const res  = await fetch("/analyze", { method: "POST" });
    const data = await res.json();

    loading.classList.add("hidden");
    analyzeBtn.disabled = false;

    if (!res.ok) {
      showStatus("error", `❌ ${data.error}`);
      return;
    }

    renderResults(data);
  } catch {
    loading.classList.add("hidden");
    analyzeBtn.disabled = false;
    showStatus("error", "❌ Analysis failed. Please try again.");
  }
});

/**
 * Render all result sections from the /analyze response.
 * @param {Object} data — JSON payload from the server
 */
function renderResults(data) {
  renderSummary(data.summary);
  renderCharts(data.charts);
  renderTopExpensesTable(data.top_expenses);
  renderInsights(data.insights);
  renderSuggestions(data.suggestions);
  resultSections.forEach(s => s.classList.remove("hidden"));
}

// ── Summary Cards ────────────────────────────────────────────
/**
 * Build the summary cards from the server's summary object.
 * Fields from the backend:
 *   total_expenses, total_income, total_transactions,
 *   expense_count, income_count, avg_transaction,
 *   highest_expense, lowest_expense, date_range, top_category
 */
function renderSummary(s = {}) {
  const cards = [
    { icon: "💸", label: "Total Expenses",      value: s.total_expenses      ?? "—", sub: `${s.expense_count ?? "—"} expense records` },
    { icon: "💰", label: "Total Income",         value: s.total_income        ?? "—", sub: `${s.income_count  ?? "—"} income records`  },
    { icon: "🔢", label: "Total Transactions",   value: s.total_transactions  ?? "—", sub: "All records"                               },
    { icon: "📊", label: "Avg. Transaction",     value: s.avg_transaction     ?? "—", sub: "Across all records"                        },
    { icon: "⬆️",  label: "Highest Expense",      value: s.highest_expense     ?? "—", sub: "Single transaction"                       },
    { icon: "⬇️",  label: "Lowest Expense",       value: s.lowest_expense      ?? "—", sub: "Single transaction"                       },
    { icon: "🏆", label: "Top Category",         value: s.top_category        ?? "—", sub: "Highest spend"                             },
    { icon: "📅", label: "Date Range",           value: s.date_range          ?? "—", sub: "First to last record"                      },
  ];

  summaryGrid.innerHTML = cards.map(c => `
    <div class="summary-card">
      <div class="summary-card__icon">${c.icon}</div>
      <div class="summary-card__label">${c.label}</div>
      <div class="summary-card__value">${c.value}</div>
      <div class="summary-card__sub">${c.sub}</div>
    </div>
  `).join("");
}

// ── Charts ───────────────────────────────────────────────────
/**
 * Render/update the three Chart.js charts using real backend data.
 * @param {Object} charts — category, monthly, top_expense arrays
 */
function renderCharts(charts = {}) {
  // Destroy existing instances before re-drawing (supports re-upload)
  if (categoryChart)    categoryChart.destroy();
  if (monthlyChart)     monthlyChart.destroy();
  if (topExpensesChart) topExpensesChart.destroy();

  // Doughnut — category spending
  categoryChart = new Chart(document.getElementById("category-chart"), {
    type: "doughnut",
    data: {
      labels: charts.category_labels ?? [],
      datasets: [{
        data: charts.category_values ?? [],
        backgroundColor: colorPalette(charts.category_labels?.length ?? 8)
      }]
    },
    options: {
      plugins: { legend: { position: "right" } },
      maintainAspectRatio: false
    }
  });

  // Bar — monthly spending trend
  monthlyChart = new Chart(document.getElementById("monthly-chart"), {
    type: "bar",
    data: {
      labels: charts.monthly_labels ?? [],
      datasets: [{
        label: "Total Spent ($)",
        data:  charts.monthly_values ?? [],
        backgroundColor: "#4361ee55",
        borderColor:     "#4361ee",
        borderWidth: 2,
        borderRadius: 5
      }]
    },
    options: {
      plugins:  { legend: { display: false } },
      scales:   { y: { beginAtZero: true } },
      maintainAspectRatio: false
    }
  });

  // Horizontal bar — top spending categories
  topExpensesChart = new Chart(document.getElementById("top-expenses-chart"), {
    type: "bar",
    data: {
      labels: charts.top_expense_labels ?? [],
      datasets: [{
        label: "Total Amount ($)",
        data:  charts.top_expense_values ?? [],
        backgroundColor: "#e6394655",
        borderColor:     "#e63946",
        borderWidth: 2,
        borderRadius: 5
      }]
    },
    options: {
      indexAxis: "y",
      plugins:   { legend: { display: false } },
      scales:    { x: { beginAtZero: true } },
      maintainAspectRatio: false
    }
  });
}

/** Return an array of n distinct chart colours. */
function colorPalette(n) {
  const base = [
    "#4361ee","#2ec4b6","#f4a261","#e63946",
    "#7c5cd8","#06d6a0","#ffd166","#ef476f",
    "#118ab2","#073b4c"
  ];
  return base.slice(0, Math.max(n, 1));
}

// ── Top 10 Transactions Table ────────────────────────────────
/**
 * Populate the top-10 expenses table.
 * @param {Array} rows — list of transaction objects from the server
 */
function renderTopExpensesTable(rows = []) {
  if (!rows.length) {
    topExpTbody.innerHTML = `<tr><td colspan="6" style="text-align:center;color:var(--color-muted)">No data available.</td></tr>`;
    return;
  }
  topExpTbody.innerHTML = rows.map((r, i) => `
    <tr>
      <td>${i + 1}</td>
      <td>${r.Date}</td>
      <td class="desc-cell">${r["Transaction Description"]}</td>
      <td><span class="category-badge">${r.Category}</span></td>
      <td class="amount-cell">$${Number(r.Amount).toLocaleString("en-US", { minimumFractionDigits: 2 })}</td>
      <td><span class="type-badge type-badge--${r.Type.toLowerCase()}">${r.Type}</span></td>
    </tr>
  `).join("");
}

// ── Insights ─────────────────────────────────────────────────
function renderInsights(insights = []) {
  insightsContent.innerHTML = insights.length
    ? insights.map(i => `
        <div class="insight-item">
          <span class="insight-item__icon">${i.icon ?? "🔍"}</span>
          <span class="insight-item__text">${i.text}</span>
        </div>`).join("")
    : "<p style='color:var(--color-muted)'>No insights available.</p>";
}

// ── Suggestions ──────────────────────────────────────────────
function renderSuggestions(suggestions = []) {
  suggestContent.innerHTML = suggestions.length
    ? suggestions.map(s => `
        <div class="suggestion-item">
          <span class="suggestion-item__icon">${s.icon ?? "💡"}</span>
          <span class="suggestion-item__text">${s.text}</span>
        </div>`).join("")
    : "<p style='color:var(--color-muted)'>No suggestions available.</p>";
}

// ── Q&A ──────────────────────────────────────────────────────
qaSubmitBtn.addEventListener("click", submitQuestion);
qaInput.addEventListener("keydown", (e) => { if (e.key === "Enter") submitQuestion(); });

async function submitQuestion() {
  const question = qaInput.value.trim();
  if (!question) return;

  qaSubmitBtn.disabled    = true;
  qaAnswerText.textContent = "Thinking…";
  qaAnswer.classList.remove("hidden");

  try {
    const res  = await fetch("/ask", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ question })
    });
    const data = await res.json();
    qaAnswerText.textContent = data.answer ?? data.error ?? "No response received.";
  } catch {
    qaAnswerText.textContent = "Request failed. Please try again.";
  } finally {
    qaSubmitBtn.disabled = false;
  }
}
