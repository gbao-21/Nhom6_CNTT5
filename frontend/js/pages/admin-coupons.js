// Trang Admin quản lý mã giảm giá
// GET    /api/coupons?role=ADMIN          -> danh sách
// POST   /api/coupons?role=ADMIN          -> tạo mới
// PATCH  /api/coupons/{id}?role=ADMIN     -> cập nhật
// PATCH  /api/coupons/{id}/deactivate?role=ADMIN -> vô hiệu hoá

const form = document.getElementById("coupon-form");
const tableBody = document.getElementById("coupon-table-body");
const formTitle = document.getElementById("form-title");
const submitButton = document.getElementById("btn-submit");
const cancelButton = document.getElementById("btn-cancel");

let editingId = null;

// ---------- Helpers ----------
function formatDatetimeLocal(isoStr) {
  if (!isoStr) return "";
  // Cắt bỏ giây và múi giờ để dùng với input[type=datetime-local]
  return isoStr.slice(0, 16);
}

function starsHtml(n) {
  return "★".repeat(n) + "☆".repeat(5 - n);
}

// ---------- Load danh sách ----------
async function loadCoupons() {
  tableBody.innerHTML = `<tr><td colspan="8" class="muted">Đang tải...</td></tr>`;
  try {
    const coupons = await api.get("/coupons", { role: "ADMIN" });
    renderCoupons(coupons);
  } catch (error) {
    tableBody.innerHTML = `<tr><td colspan="8" class="text-error">${escapeHtml(error.message)}</td></tr>`;
  }
}

function renderCoupons(coupons) {
  if (!coupons || coupons.length === 0) {
    tableBody.innerHTML = `<tr><td colspan="8" class="muted">Chưa có mã giảm giá nào.</td></tr>`;
    return;
  }
  tableBody.innerHTML = coupons.map((c) => {
    const typeLabel = c.discount_type === "PERCENT" ? `${c.discount_value}%` : formatMoney(c.discount_value);
    const minOrder = c.min_order_amount ? formatMoney(c.min_order_amount) : "—";
    const maxUses = c.max_uses ? c.max_uses : "∞";
    const used = c.used_count ?? 0;
    const validFrom = c.valid_from ? formatDatetimeLocal(c.valid_from).replace("T", " ") : "—";
    const validTo = c.valid_to ? formatDatetimeLocal(c.valid_to).replace("T", " ") : "—";
    const statusClass = c.status === "ACTIVE" ? "color:var(--color-success);font-weight:600;" : "color:var(--color-muted);";
    const statusLabel = c.status === "ACTIVE" ? "Hoạt động" : "Đã tắt";
    return `
    <tr>
      <td><strong>${escapeHtml(c.code)}</strong><div class="muted" style="font-size:12px;">${escapeHtml(c.description || "")}</div></td>
      <td>${c.discount_type === "PERCENT" ? "Phần trăm" : "Cố định"}</td>
      <td>${typeLabel}</td>
      <td>${minOrder}</td>
      <td>${used}/${maxUses}</td>
      <td style="font-size:12px;">${validFrom}<br>${validTo}</td>
      <td style="${statusClass}">${statusLabel}</td>
      <td class="actions">
        <button class="btn btn-small" data-action="edit" data-id="${c.id}">Sửa</button>
        ${c.status === "ACTIVE"
          ? `<button class="btn btn-small btn-danger" data-action="deactivate" data-id="${c.id}">Vô hiệu</button>`
          : ""}
      </td>
    </tr>`;
  }).join("");
}

// ---------- Thêm / Sửa ----------
form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = {
    code: form.code.value.trim().toUpperCase(),
    description: form.description.value.trim() || null,
    discount_type: form.discount_type.value,
    discount_value: Number(form.discount_value.value),
    min_order_amount: form.min_order_amount.value ? Number(form.min_order_amount.value) : 0,
    max_uses: form.max_uses.value ? Number(form.max_uses.value) : null,
    valid_from: form.valid_from.value ? form.valid_from.value + ":00" : null,
    valid_to: form.valid_to.value ? form.valid_to.value + ":00" : null,
  };

  submitButton.disabled = true;
  try {
    if (editingId === null) {
      await api.post("/coupons", data, { role: "ADMIN" });
      showToast("Đã tạo mã giảm giá");
    } else {
      await api.patch(`/coupons/${editingId}`, data, { role: "ADMIN" });
      showToast("Đã cập nhật mã giảm giá");
    }
    resetForm();
    loadCoupons();
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    submitButton.disabled = false;
  }
});

async function startEdit(id) {
  try {
    // Lấy từ danh sách hiện tại bằng cách gọi lại
    const coupons = await api.get("/coupons", { role: "ADMIN" });
    const coupon = coupons.find((c) => c.id === id);
    if (!coupon) { showToast("Không tìm thấy mã", "error"); return; }

    editingId = id;
    form.code.value = coupon.code;
    form.description.value = coupon.description || "";
    form.discount_type.value = coupon.discount_type;
    form.discount_value.value = coupon.discount_value;
    form.min_order_amount.value = coupon.min_order_amount || "";
    form.max_uses.value = coupon.max_uses || "";
    form.valid_from.value = coupon.valid_from ? formatDatetimeLocal(coupon.valid_from) : "";
    form.valid_to.value = coupon.valid_to ? formatDatetimeLocal(coupon.valid_to) : "";

    formTitle.textContent = `Sửa mã "${coupon.code}"`;
    submitButton.textContent = "Lưu thay đổi";
    cancelButton.hidden = false;
    form.code.focus();
  } catch (error) {
    showToast(error.message, "error");
  }
}

function resetForm() {
  editingId = null;
  form.reset();
  formTitle.textContent = "Thêm mã giảm giá";
  submitButton.textContent = "Thêm";
  cancelButton.hidden = true;
}

// ---------- Vô hiệu hoá ----------
async function deactivateCoupon(id) {
  if (!confirm("Vô hiệu hoá mã giảm giá này?")) return;
  try {
    await api.patch(`/coupons/${id}/deactivate`, {}, { role: "ADMIN" });
    showToast("Đã vô hiệu hoá");
    loadCoupons();
  } catch (error) {
    showToast(error.message, "error");
  }
}

// ---------- Event delegation ----------
tableBody.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  const id = Number(button.dataset.id);
  if (button.dataset.action === "edit") startEdit(id);
  if (button.dataset.action === "deactivate") deactivateCoupon(id);
});

cancelButton.addEventListener("click", resetForm);

loadCoupons();

