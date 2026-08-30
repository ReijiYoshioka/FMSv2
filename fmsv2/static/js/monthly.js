let transactionModal;
let receiptModal;
let chatModal;
let charts = {};
let currentLat = null;
let currentLng = null;
let descriptionDebounceTimer = null;
let chatMessages = [];
let txById = {};
let searchFilter = {};

const WEEKDAYS_JA = ["日", "月", "火", "水", "木", "金", "土"];
const PIE_COLORS = [
  "#FF6384", "#36A2EB", "#FFCE56", "#4BC0C0", "#9966FF", "#FF9F40",
  "#e74c3c", "#3498db", "#f1c40f", "#1abc9c", "#9b59b6", "#e67e22",
];

document.addEventListener("DOMContentLoaded", async () => {
  const modalEl = document.getElementById("transactionModal");
  if (modalEl) transactionModal = new bootstrap.Modal(modalEl);
  const receiptModalEl = document.getElementById("receiptModal");
  if (receiptModalEl) receiptModal = new bootstrap.Modal(receiptModalEl);
  const chatModalEl = document.getElementById("chatModal");
  if (chatModalEl) chatModal = new bootstrap.Modal(chatModalEl);
  document.getElementById("chatInput")?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendChatMessage();
  });
  setupDescriptionSuggestions();

  await loadMetadata();
  populateSelects();

  const now = new Date();
  document.getElementById("monthSelector").value =
    `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;

  initMonthlyPage();
});

function populateSelects() {
  const catSelect = document.getElementById("t_category");
  const paySelect = document.getElementById("t_payment_method");

  if (catSelect) {
    const first = catSelect.options[0];
    catSelect.innerHTML = "";
    if (first) catSelect.appendChild(first);
    metadata.categories.forEach((c) => {
      const opt = document.createElement("option");
      opt.value = c.id;
      opt.textContent = c.name;
      catSelect.appendChild(opt);
    });
  }

  if (paySelect) {
    paySelect.innerHTML = "";
    const none = document.createElement("option");
    none.value = "";
    none.textContent = "(なし)";
    paySelect.appendChild(none);
    metadata.payment_methods.forEach((p) => {
      const opt = document.createElement("option");
      opt.value = p.id;
      opt.textContent = p.name;
      paySelect.appendChild(opt);
    });
  }
}

function initMonthlyPage() {
  const monthSelector = document.getElementById("monthSelector");
  if (!monthSelector) return;

  refreshMonthlyView();
  monthSelector.addEventListener("change", refreshMonthlyView);

  document.getElementById("prevMonthBtn")?.addEventListener("click", () => {
    monthSelector.value = shiftMonth(monthSelector.value, -1);
    refreshMonthlyView();
  });
  document.getElementById("nextMonthBtn")?.addEventListener("click", () => {
    monthSelector.value = shiftMonth(monthSelector.value, 1);
    refreshMonthlyView();
  });

  const catSel = document.getElementById("searchCategory");
  if (catSel) {
    metadata.categories.forEach((c) => {
      const opt = document.createElement("option");
      opt.value = c.id;
      opt.textContent = c.name;
      catSel.appendChild(opt);
    });
  }
  document.getElementById("searchApplyBtn")?.addEventListener("click", applySearch);
  document.getElementById("searchKeyword")?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") applySearch();
  });
  document.getElementById("searchClearBtn")?.addEventListener("click", () => {
    ["searchKeyword", "searchType", "searchCategory", "searchMin", "searchMax"].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.value = "";
    });
    searchFilter = {};
    loadTransactions(monthSelector.value);
  });
  document.getElementById("csvExportBtn")?.addEventListener("click", (e) => {
    e.preventDefault();
    const params = new URLSearchParams({ month: monthSelector.value });
    Object.entries(searchFilter).forEach(([k, v]) => params.set(k, v));
    window.location.href = `/api/csv?${params.toString()}`;
  });
}

function applySearch() {
  const f = {};
  const kw = document.getElementById("searchKeyword")?.value.trim();
  const type = document.getElementById("searchType")?.value;
  const cat = document.getElementById("searchCategory")?.value;
  const min = document.getElementById("searchMin")?.value;
  const max = document.getElementById("searchMax")?.value;
  if (kw) f.q = kw;
  if (type) f.type = type;
  if (cat) f.category_id = cat;
  if (min !== "") f.min = min;
  if (max !== "") f.max = max;
  searchFilter = f;
  loadTransactions(document.getElementById("monthSelector").value);
}

function refreshMonthlyView() {
  const m = document.getElementById("monthSelector").value;
  loadTransactions(m);
  loadSummaryStats(m);
  loadPieChart("monthlyCategoryChart", "category_chart", m);
  loadPieChart("monthlyPaymentChart", "payment_chart", m);
  loadBudgetProgress(m);
}

async function loadTransactions(month) {
  const listEl = document.getElementById("transactionList");
  listEl.innerHTML =
    '<div class="text-center p-4"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">読み込み中...</span></div></div>';

  try {
    const params = new URLSearchParams({ month });
    Object.entries(searchFilter).forEach(([k, v]) => params.set(k, v));
    const res = await fetch(`/api/transactions?${params.toString()}`);
    if (handleAuthError(res)) return;
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    renderTransactions(data.transactions || []);
  } catch (e) {
    console.error(e);
    listEl.innerHTML = '<div class="alert alert-danger m-3">読み込みに失敗しました</div>';
  }
}

async function loadBudgetProgress(month) {
  const el = document.getElementById("budgetProgress");
  if (!el) return;
  try {
    const res = await fetch(`/api/budget?month=${encodeURIComponent(month)}`);
    if (handleAuthError(res)) return;
    const data = await res.json();
    if (data.error) throw new Error(data.error);

    if (!data.items || data.items.length === 0) {
      el.innerHTML =
        `<div class="text-center text-muted small py-3">予算が未設定です。` +
        `<a href="${window.MANAGE_URL}#budget">設定する</a></div>`;
      return;
    }
    el.innerHTML = data.items
      .map((it) => {
        const over = it.spent > it.budget;
        const barClass = over ? "bg-danger" : it.ratio >= 80 ? "bg-warning" : "bg-success";
        const width = Math.min(it.ratio, 100);
        return `
                <div class="mb-3">
                    <div class="d-flex justify-content-between small mb-1">
                        <span class="fw-bold">${escapeHtml(it.category)}</span>
                        <span class="${over ? "text-danger fw-bold" : "text-muted"}">${formatCurrency(it.spent)} / ${formatCurrency(it.budget)}</span>
                    </div>
                    <div class="progress" role="progressbar" aria-label="${escapeHtml(it.category)}の予算進捗" aria-valuenow="${it.ratio}" aria-valuemin="0" aria-valuemax="100" style="height: 8px;">
                        <div class="progress-bar ${barClass}" style="width: ${width}%"></div>
                    </div>
                    ${over ? `<div class="small text-danger mt-1"><i class="fas fa-exclamation-triangle me-1"></i>予算を ${formatCurrency(it.spent - it.budget)} 超過</div>` : ""}
                </div>`;
      })
      .join("");
  } catch (e) {
    console.error(e);
    el.innerHTML = '<div class="text-center text-muted small py-3">予算の読み込みに失敗しました</div>';
  }
}

async function loadSummaryStats(month) {
  try {
    const [res, prevRes] = await Promise.all([
      fetch(`/api/summary?mode=monthly_stats&month=${month}`),
      fetch(`/api/summary?mode=monthly_stats&month=${shiftMonth(month, -1)}`),
    ]);
    if (handleAuthError(res)) return;
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    const prev = prevRes.ok ? await prevRes.json() : null;

    document.getElementById("summaryIncome").textContent = formatCurrency(data.income);
    document.getElementById("summaryExpense").textContent = formatCurrency(data.expense);
    document.getElementById("summaryBalance").textContent = formatCurrency(data.balance);

    if (prev && !prev.error) {
      setDelta("summaryIncomeDelta", data.income - prev.income);
      setDelta("summaryExpenseDelta", data.expense - prev.expense);
      setDelta("summaryBalanceDelta", data.balance - prev.balance);
    } else {
      ["summaryIncomeDelta", "summaryExpenseDelta", "summaryBalanceDelta"].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.textContent = "";
      });
    }

    const card = document.getElementById("summaryBalanceCard");
    if (card) {
      card.classList.remove("balance-positive", "balance-negative");
      card.classList.add(Number(data.balance) < 0 ? "balance-negative" : "balance-positive");
    }
  } catch (e) {
    console.error(e);
  }
}

function setDelta(elId, diff) {
  const el = document.getElementById(elId);
  if (!el) return;
  if (diff === 0) {
    el.textContent = "前月比 ±0";
    return;
  }
  const arrow = diff > 0 ? "▲" : "▼";
  el.textContent = `前月比 ${arrow}${formatCurrency(Math.abs(diff))}`;
}

function renderTransactions(transactions) {
  const listEl = document.getElementById("transactionList");
  listEl.innerHTML = "";
  txById = {};

  if (transactions.length === 0) {
    listEl.innerHTML = `
            <div class="text-center p-5 text-muted">
                <i class="fas fa-inbox fa-3x mb-3 text-secondary opacity-25"></i>
                <p>データがありません</p>
                <button class="btn btn-outline-primary btn-sm" data-bs-toggle="modal" data-bs-target="#transactionModal" onclick="resetForm()">最初の取引を追加</button>
            </div>`;
    return;
  }

  let lastDate = "";
  transactions.forEach((t) => {
    txById[t.id] = t;

    const tDate = t.date.split(" ")[0];
    const dateObj = new Date(t.date.replace(" ", "T"));
    const dow = WEEKDAYS_JA[dateObj.getDay()];

    if (tDate !== lastDate) {
      const dateHeader = document.createElement("div");
      dateHeader.className =
        "bg-light px-3 py-2 font-monospace fw-bold text-secondary border-bottom d-flex align-items-center";
      const dowClass = dateObj.getDay() === 0 ? "bg-danger" : dateObj.getDay() === 6 ? "bg-primary" : "bg-secondary";
      dateHeader.innerHTML = `<i class="far fa-calendar-alt me-2"></i>${tDate} <span class="small ms-2 fw-normal badge ${dowClass}">${dow}</span>`;
      listEl.appendChild(dateHeader);
      lastDate = tDate;
    }

    const itemContainer = document.createElement("div");
    itemContainer.className = "list-group-item p-0 border-start-0 border-end-0";

    const isIncome = t.type === "income";
    const amountClass = isIncome ? "text-success" : "text-danger";
    const sign = isIncome ? "+" : "";
    const catName = t.category_name || "(未分類)";
    const payName = t.payment_method_name || "-";
    const uniqueId = `trans-${t.id}`;

    const mainRow = document.createElement("div");
    mainRow.className = "d-flex justify-content-between align-items-center p-3 transaction-header";
    mainRow.setAttribute("data-bs-toggle", "collapse");
    mainRow.setAttribute("data-bs-target", `#${uniqueId}`);
    mainRow.setAttribute("role", "button");
    mainRow.setAttribute("tabindex", "0");
    mainRow.setAttribute("aria-controls", uniqueId);
    mainRow.setAttribute("aria-expanded", "false");
    mainRow.addEventListener("keydown", (ev) => {
      if (ev.key === "Enter" || ev.key === " ") {
        ev.preventDefault();
        mainRow.click();
      }
    });

    mainRow.innerHTML = `
            <div class="d-flex align-items-center flex-grow-1 overflow-hidden">
                <div class="me-3 text-center" style="width: 40px;">
                    <i class="fas ${isIncome ? "fa-arrow-down text-success" : "fa-shopping-cart text-muted"} fa-lg"></i>
                </div>
                <div class="flex-grow-1 min-w-0">
                    <div class="fw-bold text-truncate">${escapeHtml(t.description)}</div>
                    <div class="small text-muted text-truncate">
                        <span class="badge bg-light text-dark border me-1">${escapeHtml(catName)}</span>
                        <span>${escapeHtml(payName)}</span>
                        ${t.items && t.items.length > 0 ? `<span class="badge text-bg-info ms-1"><i class="fas fa-layer-group"></i> ${t.items.length}</span>` : ""}
                    </div>
                </div>
            </div>
            <div class="${amountClass} fs-5 fw-bold text-nowrap ms-2">
                ${sign}${formatCurrency(t.amount)}
            </div>
        `;

    const collapseDiv = document.createElement("div");
    collapseDiv.id = uniqueId;
    collapseDiv.className = "collapse bg-light border-top";

    let itemsHtml = "";
    if (t.items && t.items.length > 0) {
      itemsHtml = '<div class="mt-2"><small class="text-muted fw-bold">内訳:</small><ul class="list-group list-group-sm mt-1 mb-2">';
      t.items.forEach((item) => {
        itemsHtml += `
                    <li class="list-group-item d-flex justify-content-between align-items-center bg-white px-2 py-1">
                        <span>${escapeHtml(item.item_name)} <span class="badge bg-light text-secondary border ms-1">${escapeHtml(item.category_name || "")}</span></span>
                        <span>¥${Number(item.amount).toLocaleString()}</span>
                    </li>`;
      });
      itemsHtml += "</ul></div>";
    }

    const memoHtml = t.memo
      ? `<div class="mt-2 small text-muted"><i class="far fa-comment-dots me-1"></i>${escapeHtml(t.memo)}</div>`
      : "";

    collapseDiv.innerHTML = `
            <div class="p-3">
                ${memoHtml}
                ${itemsHtml}
                <div class="mt-3 text-end">
                    <button class="btn btn-sm btn-outline-secondary dup-btn me-1" data-id="${escapeHtml(t.id)}">
                        <i class="fas fa-copy me-1"></i>複製
                    </button>
                    <button class="btn btn-sm btn-outline-primary edit-btn" data-id="${escapeHtml(t.id)}">
                        <i class="fas fa-edit me-1"></i>編集
                    </button>
                </div>
            </div>
        `;
    collapseDiv.querySelector(".edit-btn").addEventListener("click", () => {
      openEditModal(txById[t.id]);
    });
    collapseDiv.querySelector(".dup-btn").addEventListener("click", () => {
      openEditModal(txById[t.id], "duplicate");
    });

    collapseDiv.addEventListener("show.bs.collapse", () => mainRow.setAttribute("aria-expanded", "true"));
    collapseDiv.addEventListener("hide.bs.collapse", () => mainRow.setAttribute("aria-expanded", "false"));

    itemContainer.appendChild(mainRow);
    itemContainer.appendChild(collapseDiv);
    listEl.appendChild(itemContainer);
  });
}

function toggleTypeUI() {
  const type = document.getElementById("t_type").value;
  const payContainer = document.getElementById("paymentMethodContainer");
  if (payContainer) {
    payContainer.style.display = type === "income" ? "none" : "";
  }
}

function syncAmountReadonly() {
  const hasItems = document.querySelectorAll(".item-row").length > 0;
  const amountEl = document.getElementById("t_amount");
  const help = document.getElementById("amountHelp");
  if (!amountEl) return;
  amountEl.readOnly = hasItems;
  amountEl.classList.toggle("bg-light", hasItems);
  if (help) {
    help.textContent = hasItems
      ? "内訳から自動計算されています（直接編集不可）"
      : "内訳がある場合は自動計算されます";
  }
}

function cacheGeolocation() {
  if (!navigator.geolocation) return;
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      currentLat = pos.coords.latitude;
      currentLng = pos.coords.longitude;
    },
    () => {
      currentLat = null;
      currentLng = null;
    },
    { timeout: 5000 }
  );
}

function setupDescriptionSuggestions() {
  const input = document.getElementById("t_description");
  if (!input) return;
  input.addEventListener("input", () => {
    clearTimeout(descriptionDebounceTimer);
    const q = input.value.trim();
    if (q.length < 2) {
      hideDescriptionSuggestions();
      return;
    }
    descriptionDebounceTimer = setTimeout(() => fetchPlaceSuggestions(q), 600);
  });
  input.addEventListener("blur", () => {
    setTimeout(hideDescriptionSuggestions, 150);
  });
}

function hideDescriptionSuggestions() {
  const dropdown = document.getElementById("descriptionSuggestions");
  if (!dropdown) return;
  dropdown.classList.add("d-none");
  dropdown.innerHTML = "";
}

async function fetchPlaceSuggestions(query) {
  try {
    const params = new URLSearchParams({ q: query });
    if (currentLat != null && currentLng != null) {
      params.set("lat", currentLat);
      params.set("lng", currentLng);
    }
    const res = await fetch(`/api/places/suggest?${params.toString()}`);
    if (!res.ok) {
      hideDescriptionSuggestions();
      return;
    }
    const data = await res.json();
    renderDescriptionSuggestions(data.suggestions || []);
  } catch (e) {
    console.error(e);
    hideDescriptionSuggestions();
  }
}

function renderDescriptionSuggestions(suggestions) {
  const dropdown = document.getElementById("descriptionSuggestions");
  if (!dropdown) return;
  if (suggestions.length === 0) {
    hideDescriptionSuggestions();
    return;
  }
  dropdown.innerHTML = "";
  suggestions.forEach((name) => {
    const item = document.createElement("button");
    item.type = "button";
    item.className = "list-group-item list-group-item-action";
    item.textContent = name;
    item.addEventListener("mousedown", (e) => {
      e.preventDefault();
      document.getElementById("t_description").value = name;
      hideDescriptionSuggestions();
    });
    dropdown.appendChild(item);
  });
  dropdown.classList.remove("d-none");
}

function resetForm() {
  document.getElementById("transactionForm").reset();
  document.getElementById("transactionForm").querySelectorAll(".is-invalid").forEach((el) => el.classList.remove("is-invalid"));
  document.getElementById("t_id").value = "";
  hideDescriptionSuggestions();
  cacheGeolocation();

  const now = new Date();
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
  document.getElementById("t_date").value = now.toISOString().slice(0, 16);

  document.getElementById("itemsContainer").innerHTML = "";
  document.getElementById("deleteBtnContainer").style.display = "none";
  document.getElementById("modalTitle").textContent = "取引登録";
  toggleTypeUI();
  syncAmountReadonly();
}

function openEditModal(t, mode = "edit") {
  if (!t) return;
  resetForm();
  const isDup = mode === "duplicate";
  document.getElementById("modalTitle").textContent = isDup ? "取引の複製" : "取引編集";
  document.getElementById("deleteBtnContainer").style.display = isDup ? "none" : "block";

  document.getElementById("t_id").value = isDup ? "" : t.id;
  if (isDup) {
    const now = new Date();
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    document.getElementById("t_date").value = now.toISOString().slice(0, 16);
  } else {
    document.getElementById("t_date").value = t.date.replace(" ", "T").slice(0, 16);
  }
  document.getElementById("t_type").value = t.type;
  document.getElementById("t_description").value = t.description;
  document.getElementById("t_payment_method").value = t.payment_method_id || "";
  document.getElementById("t_amount").value = t.amount;
  document.getElementById("t_category").value = t.category_id || "";
  document.getElementById("t_memo").value = t.memo || "";

  if (t.items && t.items.length > 0) {
    t.items.forEach((item) => addItemRow(item));
  }
  toggleTypeUI();
  syncAmountReadonly();
  transactionModal.show();
}

function addItemRow(data = null) {
  const container = document.getElementById("itemsContainer");
  const row = document.createElement("div");
  row.className = "row g-2 mb-2 align-items-end item-row";

  let catOptions = '<option value="">(分類なし)</option>';
  metadata.categories.forEach((c) => {
    const selected = data && String(data.category_id) === String(c.id) ? "selected" : "";
    catOptions += `<option value="${c.id}" ${selected}>${escapeHtml(c.name)}</option>`;
  });

  const nameVal = data ? escapeHtml(data.item_name) : "";
  const amountVal = data ? escapeHtml(data.amount) : "";

  row.innerHTML = `
        <div class="col-5">
            <input type="text" class="form-control form-control-sm item-name" placeholder="品名" aria-label="品名" value="${nameVal}">
        </div>
        <div class="col-3">
            <input type="number" class="form-control form-control-sm item-amount" placeholder="金額" aria-label="金額" min="0" step="1" inputmode="numeric" value="${amountVal}" oninput="updateTotalAmount()">
        </div>
        <div class="col-3">
             <select class="form-select form-select-sm item-category" aria-label="カテゴリー">${catOptions}</select>
        </div>
        <div class="col-1">
            <button type="button" class="btn btn-sm btn-outline-danger" aria-label="この品目を削除" onclick="this.closest('.item-row').remove(); updateTotalAmount(); syncAmountReadonly();">&times;</button>
        </div>
    `;
  container.appendChild(row);
  syncAmountReadonly();
}

function updateTotalAmount() {
  const rows = document.querySelectorAll(".item-row");
  let total = 0;
  document.querySelectorAll(".item-amount").forEach((input) => {
    total += Number(input.value) || 0;
  });
  if (rows.length > 0) {
    document.getElementById("t_amount").value = total;
  }
}

// ---- レシート読取 ----
function resetReceiptForm() {
  document.getElementById("receiptFile").value = "";
  document.getElementById("receiptResult").innerHTML = "";
}

async function submitReceipt() {
  const fileInput = document.getElementById("receiptFile");
  const resultEl = document.getElementById("receiptResult");
  const btn = document.getElementById("receiptSubmitBtn");
  if (!fileInput.files || fileInput.files.length === 0) {
    showToast("レシート画像を選択してください", "error");
    return;
  }
  const fd = new FormData();
  fd.append("image", fileInput.files[0]);
  fd.append("csrf_token", CSRF_TOKEN);
  resultEl.innerHTML = "";
  setBtnLoading(btn, true);
  try {
    const res = await fetch("/api/receipts", {
      method: "POST",
      headers: { "X-CSRF-Token": CSRF_TOKEN },
      body: fd,
    });
    if (handleAuthError(res)) return;
    const json = await res.json();
    if (res.ok) {
      receiptModal.hide();
      applyReceiptResult(json);
    } else {
      resultEl.innerHTML = `<div class="alert alert-danger py-2 mb-0">${escapeHtml(json.error || "読み取りに失敗しました")}</div>`;
    }
  } catch (e) {
    console.error(e);
    resultEl.innerHTML = '<div class="alert alert-danger py-2 mb-0">通信エラーが発生しました</div>';
  } finally {
    setBtnLoading(btn, false);
  }
}

function applyReceiptResult(data) {
  resetForm();
  document.getElementById("modalTitle").textContent = "取引登録（レシート読取）";
  if (data.date) document.getElementById("t_date").value = `${data.date}T00:00`;
  if (data.description) document.getElementById("t_description").value = data.description;
  (data.items || []).forEach((item) => addItemRow(item));
  toggleTypeUI();
  syncAmountReadonly();
  updateTotalAmount();
  showToast("レシートを読み取りました。内容を確認して保存してください。");
  transactionModal.show();
}

// ---- チャットで登録 ----
function resetChatForm() {
  chatMessages = [];
  document.getElementById("chatMessages").innerHTML = "";
  document.getElementById("chatResult").innerHTML = "";
  document.getElementById("chatInput").value = "";
}

function appendChatBubble(role, text) {
  const container = document.getElementById("chatMessages");
  const bubble = document.createElement("div");
  const isUser = role === "user";
  bubble.className = `d-flex ${isUser ? "justify-content-end" : "justify-content-start"} mb-2`;
  bubble.innerHTML = `<div class="p-2 rounded ${isUser ? "bg-primary text-white" : "bg-light border"}" style="max-width: 80%;">${escapeHtml(text)}</div>`;
  container.appendChild(bubble);
  container.scrollTop = container.scrollHeight;
}

async function sendChatMessage() {
  const input = document.getElementById("chatInput");
  const resultEl = document.getElementById("chatResult");
  const btn = document.getElementById("chatSendBtn");
  const text = input.value.trim();
  if (!text) return;

  appendChatBubble("user", text);
  chatMessages.push({ role: "user", text });
  input.value = "";
  resultEl.innerHTML = "";
  setBtnLoading(btn, true);
  try {
    const res = await fetch("/api/chat/parse", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": CSRF_TOKEN },
      body: JSON.stringify({ csrf_token: CSRF_TOKEN, messages: chatMessages }),
    });
    if (handleAuthError(res)) return;
    const json = await res.json();
    if (!res.ok) {
      resultEl.innerHTML = `<div class="alert alert-danger py-2 mb-0">${escapeHtml(json.error || "解析に失敗しました")}</div>`;
      return;
    }
    if (json.status === "need_more_info") {
      appendChatBubble("model", json.question);
      chatMessages.push({ role: "model", text: json.question });
    } else {
      chatModal.hide();
      applyChatResult(json);
    }
  } catch (e) {
    console.error(e);
    resultEl.innerHTML = '<div class="alert alert-danger py-2 mb-0">通信エラーが発生しました</div>';
  } finally {
    setBtnLoading(btn, false);
  }
}

function applyChatResult(data) {
  resetForm();
  document.getElementById("modalTitle").textContent = "取引登録（チャット入力）";
  if (data.date) document.getElementById("t_date").value = `${data.date}T00:00`;
  if (data.description) document.getElementById("t_description").value = data.description;
  if (data.amount != null) document.getElementById("t_amount").value = data.amount;
  if (data.type) document.getElementById("t_type").value = data.type;
  if (data.category_id) document.getElementById("t_category").value = data.category_id;
  if (data.payment_method_id) document.getElementById("t_payment_method").value = data.payment_method_id;
  toggleTypeUI();
  syncAmountReadonly();
  showToast("内容を確認して保存してください。");
  transactionModal.show();
}

async function saveTransaction() {
  const form = document.getElementById("transactionForm");
  const id = document.getElementById("t_id").value;
  const saveBtn = document.getElementById("saveBtn");

  const items = [];
  let itemError = false;
  document.querySelectorAll(".item-row").forEach((row) => {
    const nameEl = row.querySelector(".item-name");
    const amountEl = row.querySelector(".item-amount");
    const name = nameEl.value.trim();
    const amount = amountEl.value;
    nameEl.classList.remove("is-invalid");
    amountEl.classList.remove("is-invalid");

    if (name === "" && amount === "") return;
    if (name === "" || amount === "" || Number(amount) < 0) {
      if (name === "") nameEl.classList.add("is-invalid");
      if (amount === "" || Number(amount) < 0) amountEl.classList.add("is-invalid");
      itemError = true;
      return;
    }
    items.push({
      item_name: name,
      amount: Number(amount),
      category_id: row.querySelector(".item-category").value || null,
    });
  });

  if (itemError) {
    showToast("内訳は品名と0以上の金額を両方入力してください。", "error");
    return;
  }

  if (!form.reportValidity()) return;

  const payload = {
    csrf_token: CSRF_TOKEN,
    id: id || null,
    date: document.getElementById("t_date").value,
    type: document.getElementById("t_type").value,
    description: document.getElementById("t_description").value,
    payment_method_id: document.getElementById("t_payment_method").value || null,
    category_id: document.getElementById("t_category").value || null,
    amount: Number(document.getElementById("t_amount").value),
    memo: document.getElementById("t_memo").value,
    items: items,
  };

  setBtnLoading(saveBtn, true);
  try {
    const res = await fetch("/api/transactions", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": CSRF_TOKEN },
      body: JSON.stringify(payload),
    });
    if (handleAuthError(res)) return;
    const json = await res.json();

    if (res.ok) {
      transactionModal.hide();
      showToast(id ? "取引を更新しました" : "取引を登録しました");
      refreshMonthlyView();
    } else {
      showToast(json.error || "保存に失敗しました", "error");
    }
  } catch (e) {
    console.error(e);
    showToast("通信エラーが発生しました", "error");
  } finally {
    setBtnLoading(saveBtn, false);
  }
}

async function deleteTransaction() {
  const id = document.getElementById("t_id").value;
  if (!id) return;

  const t = txById[id];
  const label = t ? `「${t.description} ${t.date.split(" ")[0]} ${formatCurrency(t.amount)}」` : "この取引";
  if (!confirm(`${label}を削除しますか？\nこの操作は取り消せません。`)) return;

  const deleteBtn = document.getElementById("deleteBtn");
  setBtnLoading(deleteBtn, true);
  try {
    const res = await fetch(`/api/transactions/${id}`, {
      method: "DELETE",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": CSRF_TOKEN },
      body: JSON.stringify({ csrf_token: CSRF_TOKEN }),
    });
    if (handleAuthError(res)) return;
    const json = await res.json();

    if (res.ok) {
      transactionModal.hide();
      showToast("取引を削除しました");
      refreshMonthlyView();
    } else {
      showToast(json.error || "削除に失敗しました", "error");
    }
  } catch (e) {
    console.error(e);
    showToast("通信エラーが発生しました", "error");
  } finally {
    setBtnLoading(deleteBtn, false);
  }
}

function toggleChartEmpty(canvasId, isEmpty) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  const box = ctx.closest(".chart-box");
  const empty = box?.querySelector(".chart-empty");
  if (empty) empty.classList.toggle("d-none", !isEmpty);
  ctx.style.visibility = isEmpty ? "hidden" : "visible";
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
        plugins: {
          tooltip: { callbacks: { label: (c) => `${c.label}: ${formatCurrency(c.parsed)}` } },
        },
      },
    });
  } catch (e) {
    console.error(e);
    toggleChartEmpty(canvasId, true);
  }
}
