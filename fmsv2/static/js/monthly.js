const PIE_COLORS = [
  "#4e73df", "#1cc88a", "#36b9cc", "#f6c23e", "#e74a3b",
  "#858796", "#5a5c69", "#2e59d9", "#17a673", "#2c9faf",
];

let txById = {};
const charts = {};

function currentMonth() {
  return document.getElementById("monthInput").value;
}

function shiftMonth(month, delta) {
  const [y, m] = month.split("-").map(Number);
  const total = y * 12 + (m - 1) + delta;
  const newY = Math.floor(total / 12);
  const newM = (total % 12) + 1;
  return `${newY}-${String(newM).padStart(2, "0")}`;
}

function renderChart(canvasId, labels, values, valueKey) {
  const canvas = document.getElementById(canvasId);
  if (charts[canvasId]) {
    charts[canvasId].destroy();
  }
  if (!labels.length) {
    return;
  }
  charts[canvasId] = new Chart(canvas, {
    type: "doughnut",
    data: {
      labels,
      datasets: [{ data: values, backgroundColor: PIE_COLORS }],
    },
    options: {
      plugins: {
        tooltip: {
          callbacks: {
            label: (ctx) => `${ctx.label}: ${formatCurrency(ctx.parsed)}`,
          },
        },
      },
    },
  });
}

async function loadFilterOptions() {
  const meta = await loadMetadata();
  const categorySelects = document.querySelectorAll('select[name="category_id"]');
  const paymentSelects = document.querySelectorAll('select[name="payment_method_id"]');
  categorySelects.forEach((select) => {
    const keepFirst = select.closest("#filterForm") !== null;
    select.innerHTML = keepFirst ? '<option value="">カテゴリー</option>' : '<option value="">未分類</option>';
    meta.categories.forEach((c) => {
      const opt = document.createElement("option");
      opt.value = c.id;
      opt.textContent = c.name;
      select.appendChild(opt);
    });
  });
  paymentSelects.forEach((select) => {
    select.innerHTML = '<option value="">未設定</option>';
    meta.payment_methods.forEach((p) => {
      const opt = document.createElement("option");
      opt.value = p.id;
      opt.textContent = p.name;
      select.appendChild(opt);
    });
  });
}

function addItemRow(item = {}) {
  const container = document.getElementById("itemRows");
  const row = document.createElement("div");
  row.className = "row g-2 mb-1 item-row";
  row.innerHTML = `
    <div class="col-5"><input type="text" class="form-control item-name" placeholder="品名" value="${escapeHtml(item.item_name || "")}"></div>
    <div class="col-4"><input type="number" class="form-control item-amount" placeholder="金額" value="${item.amount ?? ""}"></div>
    <div class="col-2"><select class="form-select item-category"></select></div>
    <div class="col-1"><button type="button" class="btn btn-outline-danger remove-item-btn">×</button></div>
  `;
  container.appendChild(row);
  row.querySelector(".remove-item-btn").addEventListener("click", () => {
    row.remove();
    recomputeAmountFromItems();
  });
  row.querySelector(".item-amount").addEventListener("input", recomputeAmountFromItems);
  loadMetadata().then((meta) => {
    const select = row.querySelector(".item-category");
    select.innerHTML = '<option value="">未分類</option>';
    meta.categories.forEach((c) => {
      const opt = document.createElement("option");
      opt.value = c.id;
      opt.textContent = c.name;
      if (item.category_id === c.id) opt.selected = true;
      select.appendChild(opt);
    });
  });
}

function collectItems() {
  return Array.from(document.querySelectorAll("#itemRows .item-row"))
    .map((row) => ({
      item_name: row.querySelector(".item-name").value.trim(),
      amount: Number(row.querySelector(".item-amount").value || 0),
      category_id: row.querySelector(".item-category").value || null,
    }))
    .filter((item) => item.item_name);
}

function recomputeAmountFromItems() {
  const items = collectItems();
  const amountInput = document.querySelector('#transactionForm input[name="amount"]');
  if (items.length) {
    amountInput.value = items.reduce((sum, item) => sum + item.amount, 0);
    amountInput.readOnly = true;
  } else {
    amountInput.readOnly = false;
  }
}

function renderTransactionList(transactions, meta) {
  const categoryNames = Object.fromEntries(meta.categories.map((c) => [c.id, c.name]));
  const paymentNames = Object.fromEntries(meta.payment_methods.map((p) => [p.id, p.name]));

  txById = {};
  const tbody = document.getElementById("transactionList");
  tbody.innerHTML = "";
  transactions.forEach((tx) => {
    txById[tx.id] = tx;
    const tr = document.createElement("tr");
    tr.style.cursor = "pointer";
    tr.innerHTML = `
      <td>${escapeHtml(tx.date.slice(0, 10))}</td>
      <td>${escapeHtml(tx.description)}</td>
      <td>${escapeHtml(categoryNames[tx.category_id] || "")}</td>
      <td>${escapeHtml(paymentNames[tx.payment_method_id] || "")}</td>
      <td class="text-end">${formatCurrency(tx.amount)}</td>
    `;
    tr.addEventListener("click", () => openTransactionModal(tx));
    tbody.appendChild(tr);
  });
}

function openTransactionModal(tx) {
  const form = document.getElementById("transactionForm");
  form.reset();
  document.getElementById("itemRows").innerHTML = "";
  document.getElementById("deleteTransactionBtn").classList.toggle("d-none", !tx);
  if (tx) {
    form.id.value = tx.id;
    form.date.value = tx.date.slice(0, 10);
    form.type.value = tx.type;
    form.description.value = tx.description;
    form.memo.value = tx.memo || "";
    setTimeout(() => {
      form.payment_method_id.value = tx.payment_method_id || "";
      form.category_id.value = tx.category_id || "";
    }, 0);
    (tx.items || []).forEach(addItemRow);
    form.amount.value = tx.amount;
    recomputeAmountFromItems();
  } else {
    form.date.value = currentMonth() + "-01";
  }
  new bootstrap.Modal(document.getElementById("transactionModal")).show();
}

async function loadMonth(month) {
  document.getElementById("monthInput").value = month;
  const params = new URLSearchParams(new FormData(document.getElementById("filterForm")));
  params.set("month", month);

  const [stats, prevStats, listing, categoryChart, paymentChart, budget] = await Promise.all([
    apiFetchJson(`/api/summary?mode=monthly_stats&month=${month}`),
    apiFetchJson(`/api/summary?mode=monthly_stats&month=${shiftMonth(month, -1)}`),
    apiFetchJson(`/api/transactions?${params.toString()}`),
    apiFetchJson(`/api/summary?mode=category_chart&month=${month}`),
    apiFetchJson(`/api/summary?mode=payment_chart&month=${month}`),
    apiFetchJson(`/api/budget?month=${month}`),
  ]);

  document.getElementById("incomeTotal").textContent = formatCurrency(stats.income);
  document.getElementById("expenseTotal").textContent = formatCurrency(stats.expense);
  const balanceEl = document.getElementById("balanceTotal");
  balanceEl.textContent = formatCurrency(stats.balance);
  balanceEl.className = "fs-4 " + (stats.balance >= 0 ? "balance-positive" : "balance-negative");

  document.getElementById("incomeDelta").textContent = `前月比: ${formatCurrency(stats.income - prevStats.income)}`;
  document.getElementById("expenseDelta").textContent = `前月比: ${formatCurrency(stats.expense - prevStats.expense)}`;
  document.getElementById("balanceDelta").textContent = `前月比: ${formatCurrency(stats.balance - prevStats.balance)}`;

  renderTransactionList(listing.transactions, await loadMetadata());
  renderChart("categoryChart", categoryChart.map((r) => r.category), categoryChart.map((r) => r.value));
  renderChart("paymentChart", paymentChart.map((r) => r.payment_method), paymentChart.map((r) => r.value));

  const progressEl = document.getElementById("budgetProgress");
  progressEl.innerHTML = budget.items
    .map(
      (item) => `
    <div class="mb-2">
      <div class="d-flex justify-content-between small"><span>${escapeHtml(item.category)}</span>
        <span>${formatCurrency(item.spent)} / ${formatCurrency(item.budget)}</span></div>
      <div class="budget-bar"><div class="budget-bar-fill ${item.ratio > 100 ? "over" : ""}"
        style="width: ${Math.min(item.ratio, 100)}%"></div></div>
    </div>`
    )
    .join("");

  document.getElementById("csvExportLink").href = `/api/csv?${params.toString()}`;
}

document.addEventListener("DOMContentLoaded", async () => {
  const now = new Date();
  document.getElementById("monthInput").value = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;

  await loadFilterOptions();
  await loadMonth(currentMonth());

  document.getElementById("prevMonthBtn").addEventListener("click", () => loadMonth(shiftMonth(currentMonth(), -1)));
  document.getElementById("nextMonthBtn").addEventListener("click", () => loadMonth(shiftMonth(currentMonth(), 1)));
  document.getElementById("monthInput").addEventListener("change", () => loadMonth(currentMonth()));
  document.getElementById("filterForm").addEventListener("submit", (e) => {
    e.preventDefault();
    loadMonth(currentMonth());
  });
  document.getElementById("newTransactionBtn").addEventListener("click", () => openTransactionModal(null));
  document.getElementById("addItemBtn").addEventListener("click", () => addItemRow());

  document.getElementById("transactionForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.target;
    const payload = {
      id: form.id.value || undefined,
      date: form.date.value,
      type: form.type.value,
      description: form.description.value,
      payment_method_id: form.payment_method_id.value || null,
      category_id: form.category_id.value || null,
      amount: Number(form.amount.value || 0),
      memo: form.memo.value,
      items: collectItems(),
    };
    try {
      await apiFetchJson("/api/transactions", { method: "POST", body: JSON.stringify(payload) });
      bootstrap.Modal.getInstance(document.getElementById("transactionModal")).hide();
      showToast("保存しました。");
      loadMonth(currentMonth());
    } catch (err) {
      showToast(err.message);
    }
  });

  document.getElementById("deleteTransactionBtn").addEventListener("click", async () => {
    const id = document.querySelector('#transactionForm input[name="id"]').value;
    if (!id) return;
    try {
      await apiFetchJson(`/api/transactions/${id}`, { method: "DELETE" });
      bootstrap.Modal.getInstance(document.getElementById("transactionModal")).hide();
      showToast("削除しました。");
      loadMonth(currentMonth());
    } catch (err) {
      showToast(err.message);
    }
  });
});
