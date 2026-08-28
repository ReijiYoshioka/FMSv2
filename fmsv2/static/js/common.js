const CSRF_TOKEN = document.querySelector('meta[name="csrf-token"]').content;

let toastInstance = null;
function showToast(message) {
  const toastEl = document.getElementById("appToast");
  if (!toastEl) {
    return;
  }
  toastEl.querySelector(".toast-body").textContent = message;
  if (!toastInstance) {
    toastInstance = new bootstrap.Toast(toastEl);
  }
  toastInstance.show();
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text ?? "";
  return div.innerHTML;
}

function formatCurrency(amount) {
  return "¥" + Number(amount || 0).toLocaleString("ja-JP");
}

async function handleAuthError(res) {
  if (res.status === 401) {
    showToast("認証が必要です。ログインページへ移動します。");
    setTimeout(() => {
      window.location.href = "/login";
    }, 1000);
    return true;
  }
  return false;
}

async function apiFetch(url, options = {}) {
  const opts = { ...options, headers: { ...(options.headers || {}) } };
  if (opts.method && opts.method !== "GET") {
    opts.headers["X-CSRF-Token"] = CSRF_TOKEN;
    if (opts.body && !(opts.body instanceof FormData) && !opts.headers["Content-Type"]) {
      opts.headers["Content-Type"] = "application/json";
    }
  }
  const res = await fetch(url, opts);
  if (await handleAuthError(res)) {
    throw new Error("unauthorized");
  }
  return res;
}

async function apiFetchJson(url, options = {}) {
  const res = await apiFetch(url, options);
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error || "リクエストに失敗しました。");
  }
  return data;
}

let metadataCache = null;
async function loadMetadata() {
  if (metadataCache) {
    return metadataCache;
  }
  metadataCache = await apiFetchJson("/api/transactions?action=metadata");
  return metadataCache;
}
