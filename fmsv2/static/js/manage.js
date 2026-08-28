let recurringModal;

document.addEventListener("DOMContentLoaded", async () => {
  const modalEl = document.getElementById("recurringModal");
  if (modalEl) recurringModal = new bootstrap.Modal(modalEl);

  await loadMetadata();

  const now = new Date();
  const ym = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  document.getElementById("recurringApplyMonth").value = ym;
  document.getElementById("budgetMonth").value = ym;

  initManagePage();
});

function populateManageSelects() {
  const catSel = document.getElementById("r_category");
  const paySel = document.getElementById("r_payment_method");
  if (catSel) {
    const cur = catSel.value;
    catSel.innerHTML = '<option value="">（未選択）</option>';
    metadata.categories.forEach((c) => {
      const o = document.createElement("option");
      o.value = c.id;
      o.textContent = c.name;
      catSel.appendChild(o);
    });
    catSel.value = cur;
  }
  if (paySel) {
    const cur = paySel.value;
    paySel.innerHTML = '<option value="">(なし)</option>';
    metadata.payment_methods.forEach((p) => {
      const o = document.createElement("option");
      o.value = p.id;
      o.textContent = p.name;
      paySel.appendChild(o);
    });
    paySel.value = cur;
  }
}

function initManagePage() {
  populateManageSelects();

  loadRecurring();
  loadBudgetEditor(document.getElementById("budgetMonth").value);

  document.getElementById("recurringSaveBtn")?.addEventListener("click", saveRecurring);
  document.getElementById("recurringDeleteBtn")?.addEventListener("click", deleteRecurring);
  document.getElementById("recurringApplyBtn")?.addEventListener("click", applyRecurring);
  document.getElementById("recurringApplyMonth")?.addEventListener("change", loadRecurring);
  document.getElementById("budgetMonth")?.addEventListener("change", (e) => loadBudgetEditor(e.target.value));
  document.getElementById("budgetCopyPrevBtn")?.addEventListener("click", copyPrevBudget);
  document.getElementById("csvImportBtn")?.addEventListener("click", importCsv);

  loadMasters();
  document.getElementById("addCatBtn")?.addEventListener("click", () => addMaster("category"));
  document.getElementById("addPayBtn")?.addEventListener("click", () => addMaster("payment"));
}

// ---- 定期取引 ----
async function loadRecurring() {
  const listEl = document.getElementById("recurringList");
  const month = document.getElementById("recurringApplyMonth")?.value || "";
  try {
    const res = await fetch(`/api/recurring?month=${encodeURIComponent(month)}`);
    if (handleAuthError(res)) return;
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    const rows = data.recurring || [];
    if (rows.length === 0) {
      listEl.innerHTML = '<div class="text-center text-muted small py-3">まだ登録がありません</div>';
      return;
    }
    listEl.innerHTML = "";
    rows.forEach((r) => {
      const item = document.createElement("div");
      item.className = "list-group-item d-flex justify-content-between align-items-center px-0";
      const sign = r.type === "income" ? "+" : "";
      const amtClass = r.type === "income" ? "text-success" : "text-danger";
      const appliedBadge = Number(r.applied_this_month)
        ? '<span class="badge bg-success ms-1">適用済み</span>'
        : '<span class="badge bg-warning text-dark ms-1">未適用</span>';
      item.innerHTML = `
                <div class="flex-grow-1 min-w-0">
                    <div class="fw-bold text-truncate">${escapeHtml(r.description)}
                        ${Number(r.active) ? "" : '<span class="badge bg-secondary ms-1">停止中</span>'}
                        ${Number(r.active) ? appliedBadge : ""}</div>
                    <div class="small text-muted">
                        毎月${Number(r.day_of_month)}日
                        <span class="badge bg-light text-dark border ms-1">${escapeHtml(r.category_name || "未分類")}</span>
                        ${r.payment_method_name ? escapeHtml(r.payment_method_name) : ""}
                    </div>
                </div>
                <div class="text-nowrap ms-2">
                    <span class="${amtClass} fw-bold me-2">${sign}${formatCurrency(r.amount)}</span>
                    <button class="btn btn-sm btn-outline-primary rec-edit" aria-label="編集"><i class="fas fa-edit"></i></button>
                </div>`;
      item.querySelector(".rec-edit").addEventListener("click", () => openRecurringEdit(r));
      listEl.appendChild(item);
    });
  } catch (e) {
    console.error(e);
    listEl.innerHTML = '<div class="text-center text-muted small py-3">読み込みに失敗しました</div>';
  }
}

function resetRecurringForm() {
  document.getElementById("recurringForm").reset();
  document.getElementById("r_id").value = "";
  document.getElementById("r_active").checked = true;
  document.getElementById("recurringModalTitle").textContent = "定期取引の追加";
  document.getElementById("recurringDeleteContainer").style.display = "none";
}

function openRecurringEdit(r) {
  resetRecurringForm();
  document.getElementById("recurringModalTitle").textContent = "定期取引の編集";
  document.getElementById("recurringDeleteContainer").style.display = "block";
  document.getElementById("r_id").value = r.id;
  document.getElementById("r_day").value = r.day_of_month;
  document.getElementById("r_type").value = r.type;
  document.getElementById("r_description").value = r.description;
  document.getElementById("r_amount").value = r.amount;
  document.getElementById("r_category").value = r.category_id || "";
  document.getElementById("r_payment_method").value = r.payment_method_id || "";
  document.getElementById("r_memo").value = r.memo || "";
  document.getElementById("r_active").checked = Number(r.active) === 1;
  recurringModal.show();
}

async function saveRecurring() {
  const form = document.getElementById("recurringForm");
  if (!form.reportValidity()) return;
  const btn = document.getElementById("recurringSaveBtn");
  const id = document.getElementById("r_id").value;
  const payload = {
    csrf_token: CSRF_TOKEN,
    id: id || null,
    day_of_month: Number(document.getElementById("r_day").value),
    type: document.getElementById("r_type").value,
    description: document.getElementById("r_description").value,
    amount: Number(document.getElementById("r_amount").value),
    category_id: document.getElementById("r_category").value || null,
    payment_method_id: document.getElementById("r_payment_method").value || null,
    memo: document.getElementById("r_memo").value,
    active: document.getElementById("r_active").checked,
  };
  setBtnLoading(btn, true);
  try {
    const res = await fetch("/api/recurring", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": CSRF_TOKEN },
      body: JSON.stringify(payload),
    });
    if (handleAuthError(res)) return;
    const json = await res.json();
    if (res.ok) {
      recurringModal.hide();
      showToast(id ? "定期取引を更新しました" : "定期取引を追加しました");
      loadRecurring();
    } else {
      showToast(json.error || "保存に失敗しました", "error");
    }
  } catch (e) {
    console.error(e);
    showToast("通信エラーが発生しました", "error");
  } finally {
    setBtnLoading(btn, false);
  }
}

async function deleteRecurring() {
  const id = document.getElementById("r_id").value;
  if (!id || !confirm("この定期取引を削除しますか？")) return;
  const btn = document.getElementById("recurringDeleteBtn");
  setBtnLoading(btn, true);
  try {
    const res = await fetch(`/api/recurring/${id}`, {
      method: "DELETE",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": CSRF_TOKEN },
      body: JSON.stringify({ csrf_token: CSRF_TOKEN }),
    });
    if (handleAuthError(res)) return;
    const json = await res.json();
    if (res.ok) {
      recurringModal.hide();
      showToast("削除しました");
      loadRecurring();
    } else {
      showToast(json.error || "削除に失敗しました", "error");
    }
  } catch (e) {
    console.error(e);
    showToast("通信エラーが発生しました", "error");
  } finally {
    setBtnLoading(btn, false);
  }
}

async function applyRecurring() {
  const month = document.getElementById("recurringApplyMonth").value;
  const btn = document.getElementById("recurringApplyBtn");
  if (!confirm(`${month} に定期取引を一括適用しますか？`)) return;
  setBtnLoading(btn, true);
  try {
    const res = await fetch("/api/recurring", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": CSRF_TOKEN },
      body: JSON.stringify({ action: "apply", month, csrf_token: CSRF_TOKEN }),
    });
    if (handleAuthError(res)) return;
    const json = await res.json();
    if (res.ok) {
      showToast(`${json.applied} 件を登録（適用済み ${json.already} 件はスキップ）`);
      loadRecurring();
    } else {
      showToast(json.error || "適用に失敗しました", "error");
    }
  } catch (e) {
    console.error(e);
    showToast("通信エラーが発生しました", "error");
  } finally {
    setBtnLoading(btn, false);
  }
}

// ---- 予算設定 ----
async function loadBudgetEditor(month) {
  const el = document.getElementById("budgetEditList");
  try {
    const res = await fetch(`/api/budget?month=${encodeURIComponent(month)}`);
    if (handleAuthError(res)) return;
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    const current = {};
    (data.items || []).forEach((it) => {
      current[it.category_id] = it.budget;
    });

    el.innerHTML =
      metadata.categories
        .map((c) => {
          const val = current[c.id] != null ? current[c.id] : "";
          return `
                <div class="input-group input-group-sm mb-2">
                    <span class="input-group-text" style="min-width: 8rem;">${escapeHtml(c.name)}</span>
                    <span class="input-group-text">¥</span>
                    <input type="number" class="form-control budget-input text-end" data-cat="${c.id}" min="0" step="1" inputmode="numeric" value="${val}" placeholder="0" aria-label="${escapeHtml(c.name)}の予算">
                </div>`;
        })
        .join("") + `<button class="btn btn-sm btn-primary mt-2" id="budgetSaveBtn"><i class="fas fa-save me-1"></i>予算を保存</button>`;

    document.getElementById("budgetSaveBtn").addEventListener("click", () => saveBudgets(month));
  } catch (e) {
    console.error(e);
    el.innerHTML = '<div class="text-center text-muted small py-3">読み込みに失敗しました</div>';
  }
}

async function saveBudgets(month) {
  const btn = document.getElementById("budgetSaveBtn");
  const inputs = document.querySelectorAll(".budget-input");
  const items = [];
  inputs.forEach((inp) => {
    const raw = inp.value.trim();
    const amount = raw === "" ? 0 : Number(raw);
    if (!Number.isFinite(amount) || amount < 0) return;
    items.push({ category_id: Number(inp.dataset.cat), amount });
  });
  setBtnLoading(btn, true);
  try {
    const res = await fetch("/api/budget", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": CSRF_TOKEN },
      body: JSON.stringify({ csrf_token: CSRF_TOKEN, month, items }),
    });
    if (handleAuthError(res)) return;
    const json = await res.json();
    if (res.ok) {
      showToast("予算を保存しました");
      loadBudgetEditor(month);
    } else {
      showToast(json.error || "予算の保存に失敗しました", "error");
    }
  } catch (e) {
    console.error(e);
    showToast("予算の保存に失敗しました", "error");
  } finally {
    setBtnLoading(btn, false);
  }
}

// ---- CSV インポート ----
async function importCsv() {
  const fileInput = document.getElementById("csvFile");
  const resultEl = document.getElementById("csvImportResult");
  const btn = document.getElementById("csvImportBtn");
  if (!fileInput.files || fileInput.files.length === 0) {
    showToast("CSVファイルを選択してください", "error");
    return;
  }
  const fd = new FormData();
  fd.append("file", fileInput.files[0]);
  fd.append("csrf_token", CSRF_TOKEN);
  setBtnLoading(btn, true);
  resultEl.innerHTML = "";
  try {
    const res = await fetch("/api/csv", {
      method: "POST",
      headers: { "X-CSRF-Token": CSRF_TOKEN },
      body: fd,
    });
    if (handleAuthError(res)) return;
    const json = await res.json();
    if (res.ok) {
      let html = `<div class="alert alert-success py-2">取込 ${json.inserted} 件`;
      if (json.skipped) html += ` / スキップ ${json.skipped} 件`;
      html += "</div>";
      if (json.errors && json.errors.length) {
        html += '<ul class="small text-danger mb-0">' + json.errors.map((e) => `<li>${escapeHtml(e)}</li>`).join("") + "</ul>";
      }
      resultEl.innerHTML = html;
      showToast(`${json.inserted} 件を取り込みました`);
      fileInput.value = "";
    } else {
      resultEl.innerHTML = `<div class="alert alert-danger py-2">${escapeHtml(json.error || "取込に失敗しました")}</div>`;
    }
  } catch (e) {
    console.error(e);
    resultEl.innerHTML = '<div class="alert alert-danger py-2">通信エラーが発生しました</div>';
  } finally {
    setBtnLoading(btn, false);
  }
}

// ---- 予算の前月コピー ----
async function copyPrevBudget() {
  const month = document.getElementById("budgetMonth").value;
  const btn = document.getElementById("budgetCopyPrevBtn");
  if (!confirm(`前月の予算を ${month} にコピーしますか？（既存の当月予算は上書きされます）`)) return;
  setBtnLoading(btn, true);
  try {
    const res = await fetch("/api/budget", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": CSRF_TOKEN },
      body: JSON.stringify({ csrf_token: CSRF_TOKEN, action: "copy_prev", month }),
    });
    if (handleAuthError(res)) return;
    const json = await res.json();
    if (res.ok) {
      showToast(`${json.copied} 件コピーしました`);
      loadBudgetEditor(month);
    } else {
      showToast(json.error || "コピーに失敗しました", "error");
    }
  } catch (e) {
    console.error(e);
    showToast("通信エラーが発生しました", "error");
  } finally {
    setBtnLoading(btn, false);
  }
}

// ---- マスタ編集（カテゴリー / 決済手段）----
async function loadMasters() {
  try {
    const res = await fetch("/api/masters");
    if (handleAuthError(res)) return;
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    metadata.categories = data.categories || [];
    metadata.payment_methods = data.payment_methods || [];
    renderMasterList("category", metadata.categories, "masterCatList");
    renderMasterList("payment", metadata.payment_methods, "masterPayList");
    populateManageSelects();
  } catch (e) {
    console.error(e);
  }
}

function renderMasterList(kind, items, containerId) {
  const el = document.getElementById(containerId);
  if (!el) return;
  if (!items.length) {
    el.innerHTML = '<div class="text-muted small py-2">項目がありません</div>';
    return;
  }
  el.innerHTML = "";
  items.forEach((it) => {
    const row = document.createElement("div");
    row.className = "input-group input-group-sm mb-1";
    row.innerHTML = `
            <input type="text" class="form-control master-name" value="${escapeHtml(it.name)}" maxlength="50" aria-label="名称">
            <button class="btn btn-outline-secondary master-rename" type="button" aria-label="改名"><i class="fas fa-save"></i></button>
            <button class="btn btn-outline-danger master-delete" type="button" aria-label="削除"><i class="fas fa-trash"></i></button>
        `;
    row.querySelector(".master-rename").addEventListener("click", () => {
      renameMaster(kind, it.id, row.querySelector(".master-name").value);
    });
    row.querySelector(".master-delete").addEventListener("click", () => {
      deleteMaster(kind, it.id, it.name);
    });
    el.appendChild(row);
  });
}

async function masterRequest(method, payload) {
  const res = await fetch("/api/masters", {
    method,
    headers: { "Content-Type": "application/json", "X-CSRF-Token": CSRF_TOKEN },
    body: JSON.stringify({ csrf_token: CSRF_TOKEN, ...payload }),
  });
  if (handleAuthError(res)) return null;
  return { ok: res.ok, json: await res.json() };
}

function refreshBudgetEditorIfCategory(kind) {
  if (kind === "category") {
    loadBudgetEditor(document.getElementById("budgetMonth").value);
  }
}

async function addMaster(kind) {
  const inputId = kind === "category" ? "newCatName" : "newPayName";
  const name = document.getElementById(inputId).value.trim();
  if (!name) {
    showToast("名称を入力してください", "error");
    return;
  }
  const r = await masterRequest("POST", { kind, name });
  if (!r) return;
  if (r.ok) {
    document.getElementById(inputId).value = "";
    showToast("追加しました");
    loadMasters();
    refreshBudgetEditorIfCategory(kind);
  } else {
    showToast(r.json.error || "追加に失敗しました", "error");
  }
}

async function renameMaster(kind, id, name) {
  name = name.trim();
  if (!name) {
    showToast("名称を入力してください", "error");
    return;
  }
  const r = await masterRequest("POST", { kind, id, name });
  if (!r) return;
  if (r.ok) {
    showToast("更新しました");
    loadMasters();
    refreshBudgetEditorIfCategory(kind);
  } else {
    showToast(r.json.error || "更新に失敗しました", "error");
  }
}

async function deleteMaster(kind, id, name) {
  if (!confirm(`「${name}」を削除しますか？`)) return;
  const r = await masterRequest("DELETE", { kind, id });
  if (!r) return;
  if (r.ok) {
    showToast("削除しました");
    loadMasters();
    refreshBudgetEditorIfCategory(kind);
  } else {
    showToast(r.json.error || "削除に失敗しました", "error");
  }
}
