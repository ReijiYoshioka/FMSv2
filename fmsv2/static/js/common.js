const CSRF_TOKEN = document.querySelector('meta[name="csrf-token"]')?.content || "";

let metadata = { categories: [], payment_methods: [] };
let toast;

document.addEventListener("DOMContentLoaded", () => {
  const toastEl = document.getElementById("appToast");
  if (toastEl) toast = new bootstrap.Toast(toastEl, { delay: 4000 });
});

function showToast(message, type = "success") {
  const el = document.getElementById("appToast");
  const body = document.getElementById("appToastBody");
  if (!el || !body || !toast) {
    if (type === "error") console.error(message);
    return;
  }
  el.classList.remove("text-bg-success", "text-bg-danger", "text-bg-info");
  el.classList.add(type === "error" ? "text-bg-danger" : type === "info" ? "text-bg-info" : "text-bg-success");
  body.textContent = message;
  toast.show();
}

function formatCurrency(num) {
  const n = Number(num) || 0;
  return (n < 0 ? "-¥" : "¥") + Math.abs(n).toLocaleString();
}

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str).replace(
    /[&<>'"]/g,
    (tag) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[tag]
  );
}

const CATEGORY_COLORS = [
  "#FF6384", "#36A2EB", "#FFCE56", "#4BC0C0", "#9966FF", "#FF9F40",
  "#e74c3c", "#3498db", "#f1c40f", "#1abc9c", "#9b59b6", "#e67e22",
];

function categoryColor(categoryId) {
  if (categoryId == null) return "#adb5bd";
  return CATEGORY_COLORS[Number(categoryId) % CATEGORY_COLORS.length];
}

function shiftMonth(monthStr, delta) {
  const [y, m] = monthStr.split("-").map(Number);
  const d = new Date(y, m - 1 + delta, 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function handleAuthError(res) {
  if (res.status === 401) {
    showToast("セッションが切れました。ログイン画面に移動します。", "error");
    setTimeout(() => {
      window.location.href = "/login";
    }, 1500);
    return true;
  }
  return false;
}

async function loadMetadata() {
  try {
    const res = await fetch("/api/transactions?action=metadata");
    if (handleAuthError(res)) return;
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    metadata.categories = data.categories || [];
    metadata.payment_methods = data.payment_methods || [];
  } catch (e) {
    console.error("Failed to load metadata", e);
    showToast("マスタデータの取得に失敗しました。ページを再読み込みしてください。", "error");
  }
}

function setBtnLoading(btn, loading) {
  if (!btn) return;
  if (loading) {
    btn.disabled = true;
    btn.dataset.originalHtml = btn.innerHTML;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>処理中...';
  } else {
    btn.disabled = false;
    if (btn.dataset.originalHtml) btn.innerHTML = btn.dataset.originalHtml;
  }
}
