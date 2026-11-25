// Màn hình nhân viên xử lý đơn (admin-orders.html):
// - Bảng 3 cột đơn theo trạng thái: Mới (PENDING), Đang chuẩn bị (CONFIRMED + PREPARING), Đang giao (DELIVERING)
// - Đơn mới có âm báo chuông (Web Audio API) + tự động làm mới
// - Nút chuyển trạng thái nhanh đúng luồng (Xác nhận -> Chuẩn bị -> Giao hàng -> Hoàn thành) & nút Huỷ đơn kèm lý do
// - Xem chi tiết món ăn, tùy chọn và ghi chú nổi bật; lọc theo ngày/trạng thái, tìm theo mã đơn/SĐT

const listColNew = document.getElementById("list-col-new");
const listColPrep = document.getElementById("list-col-prep");
const listColDeliv = document.getElementById("list-col-deliv");
const countColNew = document.getElementById("count-col-new");
const countColPrep = document.getElementById("count-col-prep");
const countColDeliv = document.getElementById("count-col-deliv");
const allOrdersTbody = document.getElementById("all-orders-tbody");

const filterForm = document.getElementById("staff-filter-form");
const filterQ = document.getElementById("filter-q");
const filterDate = document.getElementById("filter-date");
const filterStatus = document.getElementById("filter-status");
const filterSort = document.getElementById("filter-sort");
const btnResetFilter = document.getElementById("btn-reset-staff-filter");
const btnRefresh = document.getElementById("btn-staff-refresh");
const soundToggle = document.getElementById("sound-toggle");
const btnTestSound = document.getElementById("btn-test-sound");

const orderModal = document.getElementById("staff-order-modal");
const modalOrderTitle = document.getElementById("modal-order-title");
const modalOrderBody = document.getElementById("modal-order-body");
const btnCloseModal = document.getElementById("btn-close-modal");

const STATUS_LABELS = {
  PENDING: "Chờ xác nhận (Mới)",
  CONFIRMED: "Đã xác nhận",
  PREPARING: "Đang chuẩn bị",
  DELIVERING: "Đang giao",
  COMPLETED: "Hoàn thành",
  CANCELLED: "Đã huỷ",
};

const NEXT_ACTION_CONFIG = {
  PENDING: { nextStatus: "CONFIRMED", label: "✓ Xác nhận đơn", btnClass: "btn-success" },
  CONFIRMED: { nextStatus: "PREPARING", label: "🍳 Bắt đầu chế biến", btnClass: "btn-primary" },
  PREPARING: { nextStatus: "DELIVERING", label: "🛵 Giao hàng", btnClass: "btn-warning" },
  DELIVERING: { nextStatus: "COMPLETED", label: "🏁 Hoàn thành đơn", btnClass: "btn-success" },
};

let currentOrders = [];
let knownPendingOrderIds = new Set();
let isFirstLoad = true;

// ── 1. ÂM BÁO ĐƠN MỚI (WEB AUDIO API - KHÔNG CẦN FILE MP3 NGOÀI) ─────────────
function playNewOrderChime() {
  if (soundToggle && !soundToggle.checked) return;
  try {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return;
    const ctx = new AudioCtx();
    const notes = [587.33, 880]; // D5 -> A5 ("Ting-eling")
    notes.forEach((freq, idx) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(freq, ctx.currentTime + idx * 0.16);
      gain.gain.setValueAtTime(0.25, ctx.currentTime + idx * 0.16);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + idx * 0.16 + 0.45);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(ctx.currentTime + idx * 0.16);
      osc.stop(ctx.currentTime + idx * 0.16 + 0.45);
    });
  } catch (_) {
    // Trình duyệt chặn autoplay khi chưa tương tác
  }
}

btnTestSound.addEventListener("click", () => {
  playNewOrderChime();
  showToast("Đã phát âm báo đơn mới!");
});

// ── 2. TẢI DANH SÁCH ĐƠN HÀNG TỪ API /api/orders/staff ────────────────────────
async function loadStaffOrders(silent = false) {
  const params = {
    sort: filterSort.value || "desc",
  };
  if (filterQ.value.trim()) params.q = filterQ.value.trim();
  if (filterDate.value) params.date = filterDate.value;
  if (filterStatus.value) params.status = filterStatus.value;

  try {
    const orders = await api.get("/orders/staff", params);
    currentOrders = Array.isArray(orders) ? orders : [];

    // Kiểm tra xem có đơn PENDING mới nào vừa xuất hiện không để phát âm báo
    const currentPendingIds = new Set(
      currentOrders.filter((o) => o.status === "PENDING").map((o) => o.id),
    );
    if (!isFirstLoad) {
      let hasBrandNewPending = false;
      currentPendingIds.forEach((id) => {
        if (!knownPendingOrderIds.has(id)) hasBrandNewPending = true;
      });
      if (hasBrandNewPending) {
        playNewOrderChime();
        showToast("🔔 Có đơn hàng mới vừa đặt!");
      }
    }
    knownPendingOrderIds = currentPendingIds;
    isFirstLoad = false;

    renderKanbanColumns(currentOrders);
    renderAllOrdersTable(currentOrders);
  } catch (error) {
    if (!silent) showToast(error.message || "Không tải được danh sách đơn.", "error");
  }
}

// ── 3. RENDER 3 CỘT KANBAN: MỚI - ĐANG CHUẨN BỊ - ĐANG GIAO ──────────────────
function renderKanbanColumns(orders) {
  const newOrders = orders.filter((o) => o.status === "PENDING");
  const prepOrders = orders.filter((o) => o.status === "CONFIRMED" || o.status === "PREPARING");
  const delivOrders = orders.filter((o) => o.status === "DELIVERING");

  countColNew.textContent = String(newOrders.length);
  countColPrep.textContent = String(prepOrders.length);
  countColDeliv.textContent = String(delivOrders.length);

  listColNew.innerHTML = newOrders.length
    ? newOrders.map(renderOrderCardHTML).join("")
    : `<p class="muted" style="text-align:center;padding:24px 0;">Không có đơn mới</p>`;

  listColPrep.innerHTML = prepOrders.length
    ? prepOrders.map(renderOrderCardHTML).join("")
    : `<p class="muted" style="text-align:center;padding:24px 0;">Không có đơn đang chuẩn bị</p>`;

  listColDeliv.innerHTML = delivOrders.length
    ? delivOrders.map(renderOrderCardHTML).join("")
    : `<p class="muted" style="text-align:center;padding:24px 0;">Không có đơn đang giao</p>`;
}

function renderOrderCardHTML(order) {
  const items = Array.isArray(order.items) ? order.items : [];
  const nextAction = NEXT_ACTION_CONFIG[order.status];
  const canStaffCancel = ["PENDING", "CONFIRMED", "PREPARING"].includes(order.status);

  const dishesHTML = items
    .map((it) => {
      const opts = (it.selected_options || [])
        .map((o) => escapeHtml(o.name || `Tùy chọn #${o.option_id}`))
        .join(", ");
      return `
        <div class="staff-dish-item">
          <div>
            <strong>${Number(it.quantity)}x ${escapeHtml(it.dish_name)}</strong>
            ${opts ? `<div class="muted" style="font-size:12px;">+ ${opts}</div>` : ""}
          </div>
          ${it.note ? `<div class="dish-note-highlight">📝 Ghi chú: ${escapeHtml(it.note)}</div>` : ""}
        </div>`;
    })
    .join("");

  return `
    <article class="staff-order-card ${order.status === "PENDING" ? "is-new-order" : ""}">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;">
        <div>
          <strong style="font-size:14px;color:#ea580c;">${escapeHtml(order.order_code || `#${order.id}`)}</strong>
          <div style="font-size:13px;font-weight:700;margin-top:2px;">
            ${escapeHtml(order.recipient_name)} · <a href="tel:${escapeHtml(order.recipient_phone)}">${escapeHtml(order.recipient_phone)}</a>
          </div>
        </div>
        <span class="muted" style="font-size:11px;white-space:nowrap;">
          ${order.created_at ? formatDateTime(order.created_at) : ""}
        </span>
      </div>

      <div class="muted" style="font-size:12px;margin-top:4px;">
        📍 ${escapeHtml(order.delivery_address)}
      </div>

      <div class="staff-dish-list">
        ${dishesHTML || "<span class='muted'>Không có chi tiết món</span>"}
      </div>

      <div style="display:flex;justify-content:space-between;align-items:center;font-size:13px;">
        <span class="muted">${escapeHtml(order.payment_method)}</span>
        <strong style="color:#ea580c;">${formatMoney(order.total_amount)}</strong>
      </div>

      <div class="card-actions">
        ${
          nextAction
            ? `<button type="button" class="btn btn-small ${nextAction.btnClass}" data-action="advance" data-id="${Number(order.id)}" data-next="${nextAction.nextStatus}">
                ${nextAction.label}
              </button>`
            : ""
        }
        <button type="button" class="btn btn-small" data-action="detail" data-id="${Number(order.id)}">
          Chi tiết
        </button>
        ${
          canStaffCancel
            ? `<button type="button" class="btn btn-small btn-danger-outline" data-action="cancel" data-id="${Number(order.id)}">
                Huỷ
              </button>`
            : ""
        }
      </div>
    </article>`;
}

// ── 4. RENDER BẢNG DANH SÁCH TẤT CẢ ĐƠN HÀNG ──────────────────────────────────
function renderAllOrdersTable(orders) {
  if (orders.length === 0) {
    allOrdersTbody.innerHTML = `<tr><td colspan="7" class="muted" style="text-align:center;">Không tìm thấy đơn hàng nào khớp bộ lọc.</td></tr>`;
    return;
  }

  allOrdersTbody.innerHTML = orders
    .map((order) => {
      const items = Array.isArray(order.items) ? order.items : [];
      const itemsText = items
        .map(
          (it) =>
            `<div><strong>${Number(it.quantity)}x</strong> ${escapeHtml(it.dish_name)}${
              it.note ? ` <span class="dish-note-highlight">(${escapeHtml(it.note)})</span>` : ""
            }</div>`,
        )
        .join("");
      const nextAction = NEXT_ACTION_CONFIG[order.status];

      return `
        <tr>
          <td><strong>${escapeHtml(order.order_code || `#${order.id}`)}</strong></td>
          <td>
            <strong>${escapeHtml(order.recipient_name)}</strong><br>
            <small class="muted">${escapeHtml(order.recipient_phone)}</small>
          </td>
          <td>${itemsText || "-"}</td>
          <td><strong>${formatMoney(order.total_amount)}</strong></td>
          <td><strong>${escapeHtml(STATUS_LABELS[order.status] || order.status)}</strong></td>
          <td><small>${order.created_at ? formatDateTime(order.created_at) : ""}</small></td>
          <td>
            <div style="display:flex;gap:6px;flex-wrap:wrap;">
              ${
                nextAction
                  ? `<button type="button" class="btn btn-small ${nextAction.btnClass}" data-action="advance" data-id="${Number(order.id)}" data-next="${nextAction.nextStatus}">
                      ${nextAction.label}
                    </button>`
                  : ""
              }
              <button type="button" class="btn btn-small" data-action="detail" data-id="${Number(order.id)}">
                Xem
              </button>
            </div>
          </td>
        </tr>`;
    })
    .join("");
}

// ── 5. XỬ LÝ CHUYỂN TRẠNG THÁI NHANH, HUỶ ĐƠN & XEM CHI TIẾT ─────────────────
async function handleOrderAction(event) {
  const btn = event.target.closest("button[data-action]");
  if (!btn) return;

  const orderId = Number(btn.dataset.id);
  const action = btn.dataset.action;

  if (action === "detail") {
    const ord = currentOrders.find((o) => Number(o.id) === orderId);
    if (ord) openOrderDetailModal(ord);
    return;
  }

  if (action === "advance") {
    const nextStatus = btn.dataset.next;
    btn.disabled = true;
    try {
      await api.patch(`/orders/${orderId}/status`, {
        status: nextStatus,
        note: `Nhân viên chuyển trạng thái sang ${STATUS_LABELS[nextStatus] || nextStatus}`,
      });
      showToast(`Đã chuyển đơn sang: ${STATUS_LABELS[nextStatus] || nextStatus}`);
      await loadStaffOrders(true);
    } catch (error) {
      showToast(error.message || "Không thể chuyển trạng thái.", "error");
      btn.disabled = false;
    }
    return;
  }

  if (action === "cancel") {
    const reason = window.prompt(
      "Nhập lý do nhân viên huỷ đơn (bắt buộc, VD: Món ăn vừa hết nguyên liệu):",
      "Hết món / Hết nguyên liệu",
    );
    if (reason === null) return;
    if (!reason.trim()) {
      showToast("Nhân viên huỷ đơn bắt buộc phải nhập lý do.", "error");
      return;
    }
    btn.disabled = true;
    try {
      await api.post(`/orders/${orderId}/cancel`, {
        reason: reason.trim(),
        role: "STAFF",
      });
      showToast("Đã huỷ đơn hàng và lưu lịch sử!");
      await loadStaffOrders(true);
    } catch (error) {
      showToast(error.message || "Không thể huỷ đơn.", "error");
      btn.disabled = false;
    }
  }
}

document.querySelector(".kanban-board").addEventListener("click", handleOrderAction);
allOrdersTbody.addEventListener("click", handleOrderAction);

function openOrderDetailModal(order) {
  modalOrderTitle.textContent = `Chi tiết đơn ${order.order_code || `#${order.id}`}`;
  const items = Array.isArray(order.items) ? order.items : [];
  const histories = Array.isArray(order.status_history) ? order.status_history : [];

  modalOrderBody.innerHTML = `
    <p style="margin:4px 0;"><strong>Khách hàng:</strong> ${escapeHtml(order.recipient_name)} (${escapeHtml(order.recipient_phone)})</p>
    <p style="margin:4px 0;"><strong>Địa chỉ giao:</strong> ${escapeHtml(order.delivery_address)}</p>
    <p style="margin:4px 0;"><strong>Trạng thái hiện tại:</strong> ${escapeHtml(STATUS_LABELS[order.status] || order.status)}</p>
    <p style="margin:4px 0;"><strong>Thanh toán:</strong> ${escapeHtml(order.payment_method)} · <strong>Tổng tiền:</strong> <span style="color:#ea580c;font-weight:800;">${formatMoney(order.total_amount)}</span></p>

    <h4 style="margin:14px 0 8px;">Danh sách món & Ghi chú</h4>
    <div class="staff-dish-list">
      ${items
        .map((it) => {
          const opts = (it.selected_options || [])
            .map((o) => `${escapeHtml(o.name || `Tùy chọn #${o.option_id}`)} (+${formatMoney(o.price || 0)})`)
            .join(", ");
          return `
            <div class="staff-dish-item" style="display:flex;justify-content:space-between;gap:8px;">
              <div>
                <strong>${Number(it.quantity)}x ${escapeHtml(it.dish_name)}</strong>
                ${opts ? `<div class="muted" style="font-size:12px;">Tùy chọn: ${opts}</div>` : ""}
                ${it.note ? `<div class="dish-note-highlight">📝 Ghi chú: ${escapeHtml(it.note)}</div>` : ""}
              </div>
              <strong>${formatMoney(it.line_total)}</strong>
            </div>`;
        })
        .join("")}
    </div>

    <h4 style="margin:14px 0 8px;">Lịch sử xử lý đơn</h4>
    <ul style="margin:0;padding-left:18px;font-size:13px;">
      ${histories
        .map(
          (h) =>
            `<li><strong>${escapeHtml(STATUS_LABELS[h.new_status] || h.new_status)}</strong>${
              h.note ? ` · ${escapeHtml(h.note)}` : ""
            } <span class="muted">(${h.created_at ? formatDateTime(h.created_at) : ""})</span></li>`,
        )
        .join("")}
    </ul>
  `;
  orderModal.hidden = false;
}

btnCloseModal.addEventListener("click", () => {
  orderModal.hidden = true;
});
orderModal.addEventListener("click", (e) => {
  if (e.target === orderModal) orderModal.hidden = true;
});

// Bộ lọc
filterForm.addEventListener("submit", (e) => {
  e.preventDefault();
  loadStaffOrders(false);
});

btnResetFilter.addEventListener("click", () => {
  filterQ.value = "";
  filterDate.value = "";
  filterStatus.value = "";
  filterSort.value = "desc";
  loadStaffOrders(false);
});

btnRefresh.addEventListener("click", () => loadStaffOrders(false));

// Khởi chạy và tự động kiểm tra đơn mới mỗi 10 giây
loadStaffOrders(false);
setInterval(() => loadStaffOrders(true), 10000);

