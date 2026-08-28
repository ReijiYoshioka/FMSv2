let charts = {};

const PIE_COLORS = [
  "#FF6384", "#36A2EB", "#FFCE56", "#4BC0C0", "#9966FF", "#FF9F40",
  "#e74c3c", "#3498db", "#f1c40f", "#1abc9c", "#9b59b6", "#e67e22",
];

document.addEventListener("DOMContentLoaded", () => {
  const now = new Date();
  const yearSel = document.getElementById("reportYearSelector");
  const currentYear = now.getFullYear();
  for (let y = currentYear; y >= currentYear - 5; y--) {
    const opt = document.createElement("option");
    opt.value = y;
    opt.textContent = `${y} 年`;
    yearSel.appendChild(opt);
  }
  document.getElementById("reportMonthSelector").value =
    `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;

  initGraphsPage();
});

function toggleChartEmpty(canvasId, isEmpty) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  const box = ctx.closest(".chart-box");
  const empty = box?.querySelector(".chart-empty");
  if (empty) empty.classList.toggle("d-none", !isEmpty);
  ctx.style.visibility = isEmpty ? "hidden" : "visible";
}

function initGraphsPage() {
  const mSel = document.getElementById("reportMonthSelector");
  const ySel = document.getElementById("reportYearSelector");

  const updateMonthCharts = () => {
    loadPieChart("categoryChart", "category_chart", mSel.value);
    loadPieChart("paymentChart", "payment_chart", mSel.value);
  };
  const updateAnnualReport = () => {
    const y = ySel.value;
    loadAnnualStats(y);
    loadPieChartByYear("annualCategoryChart", "annual_category_chart", y);
    loadPieChartByYear("annualPaymentChart", "annual_payment_chart", y);
    loadTrendChart("trendChart", y);
  };

  if (mSel) {
    mSel.addEventListener("change", updateMonthCharts);
    document.getElementById("reportPrevMonthBtn")?.addEventListener("click", () => {
      mSel.value = shiftMonth(mSel.value, -1);
      updateMonthCharts();
    });
    document.getElementById("reportNextMonthBtn")?.addEventListener("click", () => {
      mSel.value = shiftMonth(mSel.value, 1);
      updateMonthCharts();
    });
    updateMonthCharts();
  }
  if (ySel) {
    ySel.addEventListener("change", updateAnnualReport);
    updateAnnualReport();
  }
}

async function loadAnnualStats(year) {
  try {
    const res = await fetch(`/api/summary?mode=annual_stats&year=${year}`);
    if (handleAuthError(res)) return;
    const data = await res.json();
    if (data.error) throw new Error(data.error);

    document.getElementById("annualIncome").textContent = formatCurrency(data.income);
    document.getElementById("annualExpense").textContent = formatCurrency(data.expense);
    document.getElementById("annualBalance").textContent = formatCurrency(data.balance);

    const card = document.getElementById("annualBalanceCard");
    if (card) {
      card.classList.remove("balance-positive", "balance-negative");
      card.classList.add(Number(data.balance) < 0 ? "balance-negative" : "balance-positive");
    }
  } catch (e) {
    console.error(e);
  }
}

async function loadPieChartByYear(canvasId, mode, year) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  if (charts[canvasId]) {
    charts[canvasId].destroy();
    charts[canvasId] = null;
  }

  try {
    const res = await fetch(`/api/summary?mode=${mode}&year=${year}`);
    if (handleAuthError(res)) return;
    const data = await res.json();

    if (!Array.isArray(data) || data.length === 0) {
      toggleChartEmpty(canvasId, true);
      return;
    }
    toggleChartEmpty(canvasId, false);

    const labelKey = mode === "annual_payment_chart" ? "payment_method" : "category";
    charts[canvasId] = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: data.map((d) => d[labelKey]),
        datasets: [{ data: data.map((d) => d.value), backgroundColor: PIE_COLORS }],
      },
      options: {
        responsive: true,
        plugins: { tooltip: { callbacks: { label: (c) => `${c.label}: ${formatCurrency(c.parsed)}` } } },
      },
    });
  } catch (e) {
    console.error(e);
    toggleChartEmpty(canvasId, true);
  }
}

async function loadPieChart(canvasId, mode, monthValue) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  if (charts[canvasId]) {
    charts[canvasId].destroy();
    charts[canvasId] = null;
  }

  try {
    const res = await fetch(`/api/summary?mode=${mode}&month=${monthValue}`);
    if (handleAuthError(res)) return;
    const data = await res.json();

    if (!Array.isArray(data) || data.length === 0) {
      toggleChartEmpty(canvasId, true);
      return;
    }
    toggleChartEmpty(canvasId, false);

    const labelKey = mode === "payment_chart" ? "payment_method" : "category";
    charts[canvasId] = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: data.map((d) => d[labelKey]),
        datasets: [{ data: data.map((d) => d.value), backgroundColor: PIE_COLORS }],
      },
      options: {
        responsive: true,
        plugins: { tooltip: { callbacks: { label: (c) => `${c.label}: ${formatCurrency(c.parsed)}` } } },
      },
    });
  } catch (e) {
    console.error(e);
    toggleChartEmpty(canvasId, true);
  }
}

async function loadTrendChart(canvasId, year) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  if (charts[canvasId]) {
    charts[canvasId].destroy();
    charts[canvasId] = null;
  }

  try {
    const res = await fetch(`/api/summary?mode=annual_trend&year=${year}`);
    if (handleAuthError(res)) return;
    const data = await res.json();

    if (!data.labels || data.labels.length === 0) {
      toggleChartEmpty(canvasId, true);
      return;
    }
    toggleChartEmpty(canvasId, false);

    const labels = data.labels.map((l) => `${Number(l.split("-")[1])}月`);

    charts[canvasId] = new Chart(ctx, {
      type: "bar",
      data: {
        labels,
        datasets: [
          { label: "収入", data: data.income, backgroundColor: "#198754" },
          { label: "支出", data: data.expense, backgroundColor: "#dc3545" },
        ],
      },
      options: {
        responsive: true,
        scales: { y: { beginAtZero: true } },
        plugins: {
          tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ${formatCurrency(c.parsed.y)}` } },
        },
      },
    });
  } catch (e) {
    console.error(e);
    toggleChartEmpty(canvasId, true);
  }
}
