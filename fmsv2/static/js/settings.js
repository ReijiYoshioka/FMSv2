document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("changePasswordBtn")?.addEventListener("click", changePassword);
});

// ---- パスワード変更 ----
async function changePassword() {
  const form = document.getElementById("passwordForm");
  if (!form.reportValidity()) return;
  const btn = document.getElementById("changePasswordBtn");
  const resultEl = document.getElementById("passwordResult");
  const cur = document.getElementById("curPassword").value;
  const nw = document.getElementById("newPassword").value;
  resultEl.innerHTML = "";
  setBtnLoading(btn, true);
  try {
    const res = await fetch("/api/account", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": CSRF_TOKEN },
      body: JSON.stringify({ csrf_token: CSRF_TOKEN, current_password: cur, new_password: nw }),
    });
    if (handleAuthError(res)) return;
    const json = await res.json();
    if (res.ok) {
      form.reset();
      resultEl.innerHTML = '<div class="alert alert-success py-2 mb-0">パスワードを変更しました</div>';
      showToast("パスワードを変更しました");
    } else {
      resultEl.innerHTML = `<div class="alert alert-danger py-2 mb-0">${escapeHtml(json.error || "変更に失敗しました")}</div>`;
    }
  } catch (e) {
    console.error(e);
    resultEl.innerHTML = '<div class="alert alert-danger py-2 mb-0">通信エラーが発生しました</div>';
  } finally {
    setBtnLoading(btn, false);
  }
}
