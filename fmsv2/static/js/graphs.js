const PIE_COLORS = [
  "#4e73df", "#1cc88a", "#36b9cc", "#f6c23e", "#e74a3b",
  "#858796", "#5a5c69", "#2e59d9", "#17a673", "#2c9faf",
];

const charts = {};

function renderDoughnut(canvasId, labels, values) {
  const canvas = document.getElementById(canvasId);
  if (charts[canvasId]) charts[canvasId].destroy();
  if (!labels.length) return;
  charts[canvasId] = new Chart(canvas, {
    type: "doughnut",
    data: { labels, datasets: [{ data: values, backgroundColor: PIE_COLORS }] },
    options: {
      plugins: {
        tooltip: { callbacks: { label: (ctx) => `${ctx.label}: ${formatCurrency(ctx.parsed)}` } },
      },
    },
  });
}

function renderTrend(labels, income, expense) {
  const canvas = document.getElementById("trendChart");
  if (charts.trendChart) charts.trendChart.destroy();
  charts.trendChart = new Chart(canvas, {
    type: "bar",
    data: {
      labels: labels.map((l) => l.slice(5)),
      datasets: [
        { label: "収入", data: income, backgroundColor: "#198754" },
        { label: "支出", data: expense, backgroundColor: "#dc3545" },
      ],
    },
  });
}

async function loadYear(year) {
  const [stats, category, payment, trend] = await Promise.all([
    apiFetchJson(`/api/summary?mode=annual_stats&year=${year}`),
    apiFetchJson(`/api/summary?mode=annual_category_chart&year=${year}`),
    apiFetchJson(`/api/summary?mode=annual_payment_chart&year=${year}`),
    apiFetchJson(`/api/summary?mode=annual_trend&year=${year}`),
  ]);
  document.getElementById("annualIncome").textContent = formatCurrency(stats.income);
  document.getElementById("annualExpense").textContent = formatCurrency(stats.expense);
  document.getElementById("annualBalance").textContent = formatCurrency(stats.balance);
  renderDoughnut("annualCategoryChart", category.map((r) => r.category), category.map((r) => r.value));
  renderDoughnut("annualPaymentChart", payment.map((r) => r.payment_method), payment.map((r) => r.value));
  renderTrend(trend.labels, trend.income, trend.expense);
}

async function loadMonth(month) {
  const [category, payment] = await Promise.all([
    apiFetchJson(`/api/summary?mode=category_chart&month=${month}`),
    apiFetchJson(`/api/summary?mode=payment_chart&month=${month}`),
  ]);
  renderDoughnut("monthlyCategoryChart", category.map((r) => r.category), category.map((r) => r.value));
  renderDoughnut("monthlyPaymentChart", payment.map((r) => r.payment_method), payment.map((r) => r.value));
}

document.addEventListener("DOMContentLoaded", () => {
  const now = new Date();
  const yearInput = document.getElementById("yearInput");
  const monthInput = document.getElementById("monthInput");
  yearInput.value = now.getFullYear();
  monthInput.value = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;

  loadYear(yearInput.value);
  loadMonth(monthInput.value);

  yearInput.addEventListener("change", () => loadYear(yearInput.value));
  monthInput.addEventListener("change", () => loadMonth(monthInput.value));
});
