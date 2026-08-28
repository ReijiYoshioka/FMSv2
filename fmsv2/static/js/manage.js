function currentYearMonth() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

// ---------- 定期取引 ----------
async function loadRecurring() {
  const month = document.getElementById("recurringMonthInput").value;
  const data = await apiFetchJson(`/api/recurring?month=${month}`);
  const tbody = document.getElementById("recurringList");
  tbody.innerHTML = data.recurring
    .map(
      (r) => `
    <tr>
      <td>${escapeHtml(r.description)}</td>
      <td>${r.day_of_month}日</td>
      <td class="text-end">${formatCurrency(r.amount)}</td>
      <td>${r.applied_this_month ? '<span class="badge bg-success">適用済</span>' : ""}</td>
      <td><button class="btn btn-sm btn-outline-danger delete-recurring-btn" data-id="${r.id}">削除</button></td>
    </tr>`
    )
    .join("");
  tbody.querySelectorAll(".delete-recurring-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      await apiFetchJson(`/api/recurring/${btn.dataset.id}`, { method: "DELETE" });
      loadRecurring();
    });
  });
}

// ---------- 予算 ----------
async function loadBudget() {
  const month = document.getElementById("budgetMonthInput").value;
  const [status, meta] = await Promise.all([
    apiFetchJson(`/api/budget?month=${month}`),
    loadMetadata(),
  ]);
  const budgetByCategory = Object.fromEntries(status.items.map((i) => [i.category_id, i.budget]));
  const tbody = document.getElementById("budgetList");
  tbody.innerHTML = meta.categories
    .map(
      (c) => `
    <tr>
      <td>${escapeHtml(c.name)}</td>
      <td><input type="number" class="form-control form-control-sm budget-amount-input"
        data-category-id="${c.id}" value="${budgetByCategory[c.id] || ""}"></td>
    </tr>`
    )
    .join("");
}

async function saveBudget() {
  const month = document.getElementById("budgetMonthInput").value;
  const items = Array.from(document.querySelectorAll(".budget-amount-input")).map((input) => ({
    category_id: Number(input.dataset.categoryId),
    amount: Number(input.value || 0),
  }));
  await apiFetchJson("/api/budget", { method: "POST", body: JSON.stringify({ month, items }) });
  showToast("予算を保存しました。");
  loadBudget();
}

// ---------- マスタ編集 ----------
let currentMasterKind = "category";

async function loadMasters() {
  const data = await apiFetchJson("/api/masters");
  const rows = currentMasterKind === "category" ? data.categories : data.payment_methods;
  const tbody = document.getElementById("masterList");
  tbody.innerHTML = rows
    .map(
      (r) => `
    <tr>
      <td>${escapeHtml(r.name)}</td>
      <td class="text-end">
        <button class="btn btn-sm btn-outline-secondary rename-master-btn" data-id="${r.id}" data-name="${escapeHtml(r.name)}">改名</button>
        <button class="btn btn-sm btn-outline-danger delete-master-btn" data-id="${r.id}">削除</button>
      </td>
    </tr>`
    )
    .join("");

  tbody.querySelectorAll(".delete-master-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      try {
        await apiFetchJson("/api/masters", {
          method: "DELETE",
          body: JSON.stringify({ kind: currentMasterKind, id: Number(btn.dataset.id) }),
        });
        loadMasters();
      } catch (err) {
        showToast(err.message);
      }
    });
  });
  tbody.querySelectorAll(".rename-master-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const name = prompt("新しい名前", btn.dataset.name);
      if (!name) return;
      try {
        await apiFetchJson("/api/masters", {
          method: "POST",
          body: JSON.stringify({ kind: currentMasterKind, id: Number(btn.dataset.id), name }),
        });
        loadMasters();
      } catch (err) {
        showToast(err.message);
      }
    });
  });
}

document.addEventListener("DOMContentLoaded", () => {
  const month = currentYearMonth();
  document.getElementById("recurringMonthInput").value = month;
  document.getElementById("budgetMonthInput").value = month;

  loadRecurring();
  loadBudget();
  loadMasters();

  document.getElementById("recurringMonthInput").addEventListener("change", loadRecurring);
  document.getElementById("budgetMonthInput").addEventListener("change", loadBudget);
  document.getElementById("saveBudgetBtn").addEventListener("click", saveBudget);

  document.getElementById("applyRecurringBtn").addEventListener("click", async () => {
    const month = document.getElementById("recurringMonthInput").value;
    const result = await apiFetchJson("/api/recurring", {
      method: "POST",
      body: JSON.stringify({ action: "apply", month }),
    });
    showToast(`適用: ${result.applied}件、既適用: ${result.already}件`);
    loadRecurring();
  });

  document.getElementById("newRecurringBtn").addEventListener("click", async () => {
    const description = prompt("内容");
    if (!description) return;
    const amount = Number(prompt("金額", "0") || 0);
    const dayOfMonth = Number(prompt("適用日(1-31)", "1") || 1);
    try {
      await apiFetchJson("/api/recurring", {
        method: "POST",
        body: JSON.stringify({
          description,
          amount,
          day_of_month: dayOfMonth,
          type: "expense",
          active: true,
        }),
      });
      loadRecurring();
    } catch (err) {
      showToast(err.message);
    }
  });

  document.getElementById("copyPrevBudgetBtn").addEventListener("click", async () => {
    const month = document.getElementById("budgetMonthInput").value;
    await apiFetchJson("/api/budget", {
      method: "POST",
      body: JSON.stringify({ action: "copy_prev", month }),
    });
    showToast("前月の予算をコピーしました。");
    loadBudget();
  });

  document.querySelectorAll("[data-kind]").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll("[data-kind]").forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      currentMasterKind = tab.dataset.kind;
      loadMasters();
    });
  });

  document.getElementById("masterAddForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const name = e.target.name.value;
    try {
      await apiFetchJson("/api/masters", {
        method: "POST",
        body: JSON.stringify({ kind: currentMasterKind, name }),
      });
      e.target.reset();
      loadMasters();
    } catch (err) {
      showToast(err.message);
    }
  });

  document.getElementById("csvImportForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    try {
      const result = await apiFetchJson("/api/csv", { method: "POST", body: formData });
      document.getElementById("csvImportResult").textContent =
        `成功: ${result.inserted}件 / スキップ: ${result.skipped}件` +
        (result.errors.length ? ` / エラー: ${result.errors.join(", ")}` : "");
    } catch (err) {
      showToast(err.message);
    }
  });

  document.getElementById("passwordForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const form = e.target;
    try {
      await apiFetchJson("/api/account", {
        method: "POST",
        body: JSON.stringify({
          current_password: form.current_password.value,
          new_password: form.new_password.value,
        }),
      });
      form.reset();
      showToast("パスワードを変更しました。");
    } catch (err) {
      showToast(err.message);
    }
  });
});
