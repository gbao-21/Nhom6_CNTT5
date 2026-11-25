// Trang khách hàng:
// 1. Đơn của tôi theo tab trạng thái (Tất cả, Chờ xác nhận, Đã xác nhận, Đang chuẩn bị, Đang giao, Hoàn thành, Đã huỷ)
// 2. Theo dõi một đơn có thanh tiến trình trạng thái tự cập nhật mỗi 15 giây
// 3. Nút huỷ đơn khi còn được phép (khi trạng thái là PENDING - Chờ xác nhận)
// 4. Đặt lại đơn & Đánh giá món ăn cho đơn đã hoàn thành (COMPLETED)

const btnLoad = document.getElementById("btn-load-order");
const orderIdInput = document.getElementById("order-id-input");
const orderInfo = document.getElementById("order-info");
const orderStatusInfo = document.getElementById("order-status-info");
const trackingProgressBar = document.getElementById("tracking-progress-bar");
const trackingOrderDetails = document.getElementById("tracking-order-details");
const cancelOrderButton = document.getElementById("cancel-order-button");
const reorderButton = document.getElementById("reorder-button");
const reviewsSection = document.getElementById("reviews-section");
const dishReviewsList = document.getElementById("dish-reviews-list");
const myOrdersTabList = document.getElementById("my-orders-tab-list");
const orderStatusTabs = document.getElementById("order-status-tabs");
const btnRefreshOrders = document.getElementById("btn-refresh-orders");
const reorderStatus = document.getElementById("reorder-status");
const pollCountdownEl = document.getElementById("poll-countdown");

const DEFAULT_USER_ID = 1;
const POLL_INTERVAL_SECONDS = 15;

const STATUS_LABELS = {
  PENDING: "Chờ xác nhận",
  CONFIRMED: "Đã xác nhận",
  PREPARING: "Đang chuẩn bị",
  DELIVERING: "Đang giao",
  COMPLETED: "Hoàn thành",
  CANCELLED: "Đã huỷ",
};

const PROGRESS_STEPS = [
  { key: "PENDING", label: "1. Chờ xác nhận", icon: "fa-clock" },
  { key: "CONFIRMED", label: "2. Đã xác nhận", icon: "fa-circle-check" },
  { key: "PREPARING", label: "3. Đang chuẩn bị", icon: "fa-fire-burner" },
  { key: "DELIVERING", label: "4. Đang giao", icon: "fa-motorcycle" },
  { key: "COMPLETED", label: "5. Hoàn thành", icon: "fa-face-smile" },
];

let allMyOrders = [];
let currentTabStatus = "ALL";
let trackedOrderId = null;
let currentOrderItems = [];
let selectedRatings = {};
let countdownSeconds = POLL_INTERVAL_SECONDS;
let pollTimer = null;

// ── 1. TẢI DANH SÁCH ĐƠN CỦA TÔI & LỌC THEO TAB TRẠNG THÁI ───────────────────
async function loadMyOrdersByTab(silent = false) {
  if (!silent) {
    myOrdersTabList.innerHTML = `<p class="muted">Đang tải danh sách đơn hàng...</p>`;
  }
  try {
    allMyOrders = await api.get("/orders/my-orders", { user_id: DEFAULT_USER_ID });
    if (!Array.isArray(allMyOrders)) allMyOrders = [];
    updateTabCounts();
    renderOrdersForActiveTab();

    // Nếu chưa chọn đơn nào để theo dõi thì tự chọn đơn mới nhất
    if (!trackedOrderId && allMyOrders.length > 0) {
      trackedOrderId = allMyOrders[0].id;
      orderIdInput.value = String(trackedOrderId);
      await loadOrder(true);
    }
  } catch (error) {
    myOrdersTabList.innerHTML = `<p class="text-error">${escapeHtml(error.message)}</p>`;
  }
}

function updateTabCounts() {
  const counts = { ALL: allMyOrders.length };
  allMyOrders.forEach((o) => {
    counts[o.status] = (counts[o.status] || 0) + 1;
  });

  const baseLabels = {
    ALL: "Tất cả",
    PENDING: "Chờ xác nhận",
    CONFIRMED: "Đã xác nhận",
    PREPARING: "Đang chuẩn bị",
    DELIVERING: "Đang giao",
    COMPLETED: "Hoàn thành",
    CANCELLED: "Đã huỷ",
  };

  orderStatusTabs.querySelectorAll(".status-tab").forEach((btn) => {
    const st = btn.dataset.status;
    const count = counts[st] || 0;
    btn.textContent = `${baseLabels[st] || st} (${count})`;
    btn.classList.toggle("active", st === currentTabStatus);
  });
}

function renderOrdersForActiveTab() {
  const filtered =
    currentTabStatus === "ALL"
      ? allMyOrders
      : allMyOrders.filter((o) => o.status === currentTabStatus);

  if (filtered.length === 0) {
    myOrdersTabList.innerHTML = `<p class="muted">Không có đơn hàng nào ở trạng thái này.</p>`;
    return;
  }

  myOrdersTabList.innerHTML = filtered
    .map((order) => {
      const items = Array.isArray(order.items) ? order.items : [];
      const itemSummary = items
        .map((it) => `${Number(it.quantity)}x ${escapeHtml(it.dish_name || `Món #${it.dish_id}`)}`)
        .join(", ");
      const canCancel = order.status === "PENDING";
      const isSelected = Number(order.id) === Number(trackedOrderId);

      return `
        <article class="order-card-item ${isSelected ? "selected-order" : ""}">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:10px;">
            <div>
              <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                <strong>${escapeHtml(order.order_code || `Đơn #${order.id}`)}</strong>
                <span class="badge-status badge-${escapeHtml(order.status)}">
                  ${escapeHtml(STATUS_LABELS[order.status] || order.status)}
                </span>
                <span class="muted" style="font-size:12px;">
                  ${order.created_at ? formatDateTime(order.created_at) : ""}
                </span>
              </div>
              <p style="margin:6px 0 4px;font-size:14px;">
                ${itemSummary || "Không có thông tin món"}
              </p>
              <div class="muted" style="font-size:13px;">
                Giao tới: ${escapeHtml(order.delivery_address)} · Tổng: <strong style="color:#ea580c;">${formatMoney(order.total_amount)}</strong>
              </div>
            </div>

            <div style="display:flex;gap:6px;flex-wrap:wrap;">
              <button type="button" class="btn btn-primary btn-small btn-track-this" data-order-id="${Number(order.id)}">
                <i class="fa-solid fa-location-crosshairs" aria-hidden="true"></i> Theo dõi đơn
              </button>
              ${
                canCancel
                  ? `<button type="button" class="btn btn-danger btn-small btn-cancel-this" data-order-id="${Number(order.id)}">
                      <i class="fa-solid fa-ban" aria-hidden="true"></i> Huỷ đơn
                    </button>`
                  : ""
              }
              <button type="button" class="btn btn-small btn-reorder-this" data-order-id="${Number(order.id)}" ${items.length === 0 ? "disabled" : ""}>
                <i class="fa-solid fa-rotate-right" aria-hidden="true"></i> Đặt lại
              </button>
            </div>
          </div>
        </article>`;
    })
    .join("");

  myOrdersTabList.querySelectorAll(".btn-track-this").forEach((btn) => {
    btn.addEventListener("click", async () => {
      trackedOrderId = Number(btn.dataset.orderId);
      orderIdInput.value = String(trackedOrderId);
      renderOrdersForActiveTab();
      await loadOrder();
      document.getElementById("tracking-card").scrollIntoView({ behavior: "smooth" });
    });
  });

  myOrdersTabList.querySelectorAll(".btn-cancel-this").forEach((btn) => {
    btn.addEventListener("click", () => {
      promptAndCancelOrder(Number(btn.dataset.orderId));
    });
  });

  myOrdersTabList.querySelectorAll(".btn-reorder-this").forEach((btn) => {
    btn.addEventListener("click", () => {
      const ord = allMyOrders.find((o) => Number(o.id) === Number(btn.dataset.orderId));
      reorderItems(ord?.items || [], btn);
    });
  });
}

orderStatusTabs.addEventListener("click", (event) => {
  const tab = event.target.closest(".status-tab");
  if (!tab) return;
  currentTabStatus = tab.dataset.status;
  updateTabCounts();
  renderOrdersForActiveTab();
});

btnRefreshOrders.addEventListener("click", () => {
  loadMyOrdersByTab();
  if (trackedOrderId) loadOrder(true);
});

// ── 2. THEO DÕI 1 ĐƠN HÀNG & THANH TIẾN TRÌNH TỰ CẬP NHẬT MỖI 15 GIÂY ─────────
btnLoad.addEventListener("click", () => loadOrder(false));
orderIdInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") loadOrder(false);
});

async function loadOrder(silent = false) {
  const orderId = orderIdInput.value.trim();
  if (!orderId) {
    if (!silent) showToast("Nhập ID đơn hàng cần theo dõi", "error");
    return;
  }
  trackedOrderId = Number(orderId);
  countdownSeconds = POLL_INTERVAL_SECONDS;

  try {
    const order = await api.get(`/orders/my-orders/${orderId}?user_id=${DEFAULT_USER_ID}`);
    currentOrderItems = Array.isArray(order.items) ? order.items : [];

    renderTrackedOrder(order);
    orderInfo.hidden = false;

    // Chỉ hiện nút Huỷ khi đơn còn ở trạng thái PENDING (Chờ xác nhận)
    cancelOrderButton.hidden = order.status !== "PENDING";
    cancelOrderButton.onclick = () => promptAndCancelOrder(order.id);

    reorderButton.hidden = currentOrderItems.length === 0;
    reorderButton.disabled = false;

    // Nếu đơn đã COMPLETED thì tải thêm phần Đánh giá món ăn
    if (order.status === "COMPLETED") {
      try {
        const reviewData = await api.get(`/reviews/order/${orderId}`);
        renderDishReviews(reviewData, orderId);
        reviewsSection.hidden = false;
      } catch (_) {
        reviewsSection.hidden = true;
      }
    } else {
      reviewsSection.hidden = true;
    }

    renderOrdersForActiveTab();
  } catch (error) {
    if (!silent) {
      showToast(error.message, "error");
      orderInfo.hidden = false;
      orderStatusInfo.innerHTML = `<p class="text-error">${escapeHtml(error.message)}</p>`;
      trackingProgressBar.innerHTML = "";
      trackingOrderDetails.innerHTML = "";
      cancelOrderButton.hidden = true;
      reorderButton.hidden = true;
      reviewsSection.hidden = true;
    }
  }
}

function renderTrackedOrder(order) {
  const status = order.status || "PENDING";
  const label = STATUS_LABELS[status] || status;

  orderStatusInfo.innerHTML = `
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
      <div>
        <strong style="font-size:1.1rem;">${escapeHtml(order.order_code || `Đơn hàng #${order.id}`)}</strong>
        <span class="badge-status badge-${escapeHtml(status)}" style="margin-left:8px;">${escapeHtml(label)}</span>
      </div>
      <span class="muted" style="font-size:13px;">
        Đặt lúc: ${order.created_at ? formatDateTime(order.created_at) : ""}
      </span>
    </div>
  `;

  // Thanh tiến trình 5 bước
  if (status === "CANCELLED") {
    trackingProgressBar.innerHTML = `
      <div style="grid-column:1 / -1;padding:12px;border-radius:8px;background:#fee2e2;color:#b91c1c;font-weight:700;text-align:center;">
        <i class="fa-solid fa-circle-xmark" aria-hidden="true"></i> Đơn hàng này đã bị huỷ
      </div>`;
  } else {
    const activeIdx = PROGRESS_STEPS.findIndex((s) => s.key === status);
    trackingProgressBar.innerHTML = PROGRESS_STEPS.map((step, idx) => {
      const cls =
        idx === activeIdx
          ? "progress-step current"
          : idx < activeIdx
          ? "progress-step done"
          : "progress-step";
      return `
        <div class="${cls}">
          <div style="font-size:1.1rem;margin-bottom:4px;">
            <i class="fa-solid ${step.icon}" aria-hidden="true"></i>
          </div>
          <div>${escapeHtml(step.label)}</div>
        </div>`;
    }).join("");
  }

  // Chi tiết món, thông tin nhận hàng và lịch sử trạng thái
  const items = Array.isArray(order.items) ? order.items : [];
  const histories = Array.isArray(order.status_history) ? order.status_history : [];

  trackingOrderDetails.innerHTML = `
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px;">
      <div style="background:#f9fafb;padding:12px;border-radius:8px;">
        <strong style="display:block;margin-bottom:8px;">Thông tin giao hàng</strong>
        <p style="margin:4px 0;font-size:13px;">Người nhận: <strong>${escapeHtml(order.recipient_name)}</strong> (${escapeHtml(order.recipient_phone)})</p>
        <p style="margin:4px 0;font-size:13px;">Địa chỉ: ${escapeHtml(order.delivery_address)}</p>
        <p style="margin:4px 0;font-size:13px;">Thanh toán: ${escapeHtml(order.payment_method)} · Tổng tiền: <strong style="color:#ea580c;">${formatMoney(order.total_amount)}</strong></p>
      </div>

      <div style="background:#f9fafb;padding:12px;border-radius:8px;">
        <strong style="display:block;margin-bottom:8px;">Các món trong đơn (${items.length})</strong>
        ${items
          .map((it) => {
            const opts = (it.selected_options || [])
              .map((o) => escapeHtml(o.name || `Tùy chọn #${o.option_id}`))
              .join(", ");
            return `
              <div style="display:flex;justify-content:space-between;font-size:13px;padding:4px 0;border-bottom:1px dashed #e5e7eb;">
                <span>
                  <strong>${Number(it.quantity)}x</strong> ${escapeHtml(it.dish_name)}
                  ${opts ? `<small class="muted"> (${opts})</small>` : ""}
                  ${it.note ? `<br><small style="color:#d97706;">Ghi chú: ${escapeHtml(it.note)}</small>` : ""}
                </span>
                <strong>${formatMoney(it.line_total)}</strong>
              </div>`;
          })
          .join("")}
      </div>
    </div>

    ${
      histories.length > 0
        ? `<div style="margin-top:12px;font-size:12px;" class="muted">
            <strong>Lịch sử cập nhật trạng thái:</strong>
            <ul style="margin:6px 0 0;padding-left:18px;">
              ${histories
                .map(
                  (h) =>
                    `<li><strong>${escapeHtml(STATUS_LABELS[h.new_status] || h.new_status)}</strong>${
                      h.note ? ` - ${escapeHtml(h.note)}` : ""
                    } (${h.created_at ? formatDateTime(h.created_at) : ""})</li>`,
                )
                .join("")}
            </ul>
          </div>`
        : ""
    }
  `;
}

// Tự động cập nhật tiến trình đơn mỗi 15 giây
function startAutoPolling15s() {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(async () => {
    countdownSeconds -= 1;
    if (countdownSeconds <= 0) {
      countdownSeconds = POLL_INTERVAL_SECONDS;
      if (trackedOrderId) {
        await loadOrder(true);
      }
      await loadMyOrdersByTab(true);
    }
    if (pollCountdownEl) {
      pollCountdownEl.textContent = String(countdownSeconds);
    }
  }, 1000);
}

// ── 3. HUỶ ĐƠN HÀNG KHI CÒN ĐƯỢC PHÉP (TRẠNG THÁI PENDING) ───────────────────
async function promptAndCancelOrder(orderId) {
  const reason = window.prompt(
    "Nhập lý do huỷ đơn hàng (chỉ huỷ được khi đơn còn ở trạng thái Chờ xác nhận):",
    "Đổi ý / Muốn đổi món khác",
  );
  if (reason === null) return;
  if (!reason.trim()) {
    showToast("Vui lòng nhập lý do huỷ đơn.", "error");
    return;
  }

  try {
    await api.post(`/orders/${orderId}/cancel`, {
      reason: reason.trim(),
      user_id: DEFAULT_USER_ID,
      role: "CUSTOMER",
    });
    showToast("Đã huỷ đơn hàng thành công!");
    await loadMyOrdersByTab(true);
    if (Number(trackedOrderId) === Number(orderId)) {
      await loadOrder(true);
    }
  } catch (error) {
    showToast(error.message || "Không thể huỷ đơn hàng.", "error");
  }
}

// ── 4. ĐẶT LẠI ĐƠN & ĐÁNH GIÁ ĐƠN HOÀN THÀNH ─────────────────────────────────
function starsHtml(rating) {
  const full = Math.round(rating);
  return "★".repeat(full) + "☆".repeat(5 - full);
}

function starInputHtml(dishId) {
  return [5, 4, 3, 2, 1]
    .map(
      (n) => `
    <input type="radio" name="rating_${dishId}" id="star_${dishId}_${n}" value="${n}" style="display:none;">
    <label for="star_${dishId}_${n}" style="cursor:pointer;font-size:1.5rem;color:#d1d5db;" 
           onmouseover="highlightStars('${dishId}',${n})" 
           onmouseout="resetStars('${dishId}')"
           onclick="selectStar('${dishId}',${n})">★</label>
  `,
    )
    .join("");
}

function highlightStars(dishId, upTo) {
  [1, 2, 3, 4, 5].forEach((n) => {
    const lbl = document.querySelector(`label[for="star_${dishId}_${n}"]`);
    if (lbl) lbl.style.color = n <= upTo ? "#f59e0b" : "#d1d5db";
  });
}

function resetStars(dishId) {
  const sel = selectedRatings[dishId] || 0;
  [1, 2, 3, 4, 5].forEach((n) => {
    const lbl = document.querySelector(`label[for="star_${dishId}_${n}"]`);
    if (lbl) lbl.style.color = n <= sel ? "#f59e0b" : "#d1d5db";
  });
}

function selectStar(dishId, rating) {
  selectedRatings[dishId] = rating;
  resetStars(dishId);
}

async function reorderItems(items, button) {
  if (!Array.isArray(items) || items.length === 0) {
    showToast("Đơn hàng không có món để đặt lại.", "error");
    return;
  }

  const originalButtonContent = button?.innerHTML;
  if (button) {
    button.disabled = true;
    button.textContent = "Đang thêm vào giỏ...";
  }
  setReorderStatus("Đang thêm các món của đơn hàng vào giỏ...", false);

  try {
    const results = [];
    for (const item of items) {
      if (!Number.isInteger(Number(item.dish_id)) || Number(item.dish_id) < 1) {
        results.push({ added: false, error: "Một món không còn thông tin để đặt lại." });
        continue;
      }

      try {
        await api.post("/carts/items", {
          dish_id: Number(item.dish_id),
          selected_options: (item.selected_options || []).map((option) => ({
            option_id: Number(option.option_id),
            name: option.name,
            price: Number(option.price) || 0,
          })),
          note: item.note || null,
          quantity: Math.max(1, Math.floor(Number(item.quantity) || 1)),
        });
        results.push({ added: true });
      } catch (error) {
        results.push({ added: false, error: error.message });
      }
    }

    const addedCount = results.filter((result) => result.added).length;
    const failedResults = results.filter((result) => !result.added);
    if (failedResults.length === 0) {
      const message = `Đã thêm ${addedCount} món vào giỏ hàng.`;
      setReorderStatus(message, false, true);
      showToast(message);
    } else if (addedCount > 0) {
      const message = `Đã thêm ${addedCount}/${items.length} món. ${failedResults.length} món chưa thêm được: ${failedResults[0].error}`;
      setReorderStatus(message, true, addedCount > 0);
      showToast(message, "error");
    } else {
      const message = `Không thể đặt lại món: ${failedResults[0].error}`;
      setReorderStatus(message, true);
      showToast(message, "error");
    }
  } finally {
    if (button) {
      button.innerHTML = originalButtonContent;
      button.disabled = false;
    }
  }
}

function setReorderStatus(message, isError, showCartLink = false) {
  reorderStatus.replaceChildren();
  reorderStatus.hidden = false;
  reorderStatus.classList.toggle("is-error", isError);
  const messageElement = document.createElement("span");
  messageElement.textContent = message;
  reorderStatus.appendChild(messageElement);

  if (showCartLink) {
    const cartLink = document.createElement("a");
    cartLink.href = "cart.html";
    cartLink.textContent = "Mở giỏ hàng";
    reorderStatus.appendChild(cartLink);
  }
}

reorderButton.addEventListener("click", async () => {
  await reorderItems(currentOrderItems, reorderButton);
});

function renderDishReviews(data, orderId) {
  const reviews = data.reviews || [];
  const isCompleted = data.order_status === "COMPLETED";

  if (reviews.length === 0 && !isCompleted) {
    dishReviewsList.innerHTML = `<p class="muted">Đơn hàng chưa có thông tin để hiển thị.</p>`;
    return;
  }

  if (reviews.length === 0 && isCompleted) {
    dishReviewsList.innerHTML =
      `<p class="muted">Đơn hàng chưa được đánh giá món nào. Hãy dùng form bên dưới.</p>` +
      renderNewReviewForm(orderId, null);
    return;
  }

  dishReviewsList.innerHTML = reviews
    .map((r) => {
      const hasReview = r.id !== null && r.id !== undefined;
      return `
      <div style="border:1px solid var(--color-border);border-radius:var(--radius);padding:16px;margin-bottom:12px;">
        <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
          <strong>${escapeHtml(r.dish_name || "Món " + r.dish_id)}</strong>
          ${
            hasReview
              ? `<span style="color:#f59e0b;">${starsHtml(r.rating)} ${r.rating}/5</span>`
              : isCompleted
              ? `<span class="muted" style="font-size:13px;">Chưa đánh giá</span>`
              : ""
          }
        </div>
        ${
          hasReview
            ? `
          <p style="margin:6px 0;">${escapeHtml(r.content || "")}</p>
          ${r.image_url ? `<img src="${escapeHtml(r.image_url)}" alt="" style="max-height:100px;border-radius:4px;">` : ""}
          <div class="muted" style="font-size:12px;margin-top:4px;">${r.created_at ? formatDateTime(r.created_at) : ""}</div>
        `
            : isCompleted
            ? renderNewReviewForm(orderId, r.dish_id, r.dish_name)
            : ""
        }
      </div>`;
    })
    .join("");
}

function renderNewReviewForm(orderId, dishId, dishName) {
  const dishIdInput = dishId
    ? `<input type="hidden" id="dish_id_field_${dishId}" value="${dishId}">`
    : `<div>
        <label>ID món ăn *</label>
        <input type="number" id="dish_id_field_new" min="1" placeholder="Nhập ID món" style="width:120px;">
       </div>`;
  const title = dishId ? dishName || `Món ${dishId}` : "Món mới";

  return `
    <form class="review-form" data-order="${orderId}" data-dish="${dishId || ""}" style="margin-top:12px;padding:12px;background:var(--color-bg);border-radius:var(--radius);">
      <strong style="display:block;margin-bottom:8px;">Đánh giá${dishId ? ": " + escapeHtml(title) : ""}</strong>
      ${dishIdInput}
      <div style="margin:8px 0;">
        <label style="margin:0 0 4px;">Số sao *</label>
        <div class="star-input" data-dish="${dishId || "new"}">
          ${starInputHtml(dishId || "new")}
        </div>
      </div>
      <label>Nhận xét</label>
      <textarea class="review-content" rows="2" placeholder="Nhập nhận xét..." style="margin-top:4px;"></textarea>
      <label>Ảnh (URL)</label>
      <input class="review-image" type="url" placeholder="https://...">
      <button type="submit" class="btn btn-primary btn-small" style="margin-top:10px;">Gửi đánh giá</button>
    </form>`;
}

dishReviewsList.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.target;
  if (!form.classList.contains("review-form")) return;

  const orderId = Number(form.dataset.order);
  let dishId = form.dataset.dish ? Number(form.dataset.dish) : null;

  if (!dishId) {
    const manualInput = form.querySelector("#dish_id_field_new");
    dishId = manualInput ? Number(manualInput.value) : null;
  }
  if (!dishId) {
    showToast("Nhập ID món ăn", "error");
    return;
  }

  const dishKey = form.dataset.dish || "new";
  const rating = selectedRatings[dishKey];
  if (!rating) {
    showToast("Chọn số sao", "error");
    return;
  }

  const content = form.querySelector(".review-content").value.trim();
  const imageUrl = form.querySelector(".review-image").value.trim() || null;

  const submitBtn = form.querySelector("button[type=submit]");
  submitBtn.disabled = true;

  try {
    await api.post("/reviews", {
      order_id: orderId,
      dish_id: dishId,
      user_id: DEFAULT_USER_ID,
      rating,
      content: content || null,
      image_url: imageUrl,
    });
    showToast("Đã gửi đánh giá!");
    loadOrder(true);
  } catch (error) {
    showToast(error.message, "error");
    submitBtn.disabled = false;
  }
});

// Khởi tạo trang
const urlOrderId = new URLSearchParams(window.location.search).get("order_id");
if (urlOrderId) {
  trackedOrderId = Number(urlOrderId);
  orderIdInput.value = urlOrderId;
  loadOrder(false);
}
loadMyOrdersByTab(false);
startAutoPolling15s();
