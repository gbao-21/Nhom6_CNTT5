// Logic trang Kết quả đặt món (order-result.html):
// - Hiển thị trang đặt món thành công kèm Mã đơn hàng (order_code) + nút Sao chép mã + nút Theo dõi đơn hàng
// - Hiển thị dòng thời gian theo dõi trạng thái đơn trực tiếp & dẫn sang trang Đơn của tôi (my-orders.html?order_id=...)
// - Báo lỗi rõ ràng khi món vừa hết hàng trong lúc đặt (kèm nút tự động xoá món hết khỏi giỏ để đặt tiếp)
// - Hiển thị và xác nhận lựa chọn thanh toán đã lưu cho lần đặt sau (localStorage)

const LAST_ORDER_STORAGE_KEY = "bepviet_last_order_v1";
const LAST_ORDER_ERROR_KEY = "bepviet_last_order_error_v1";
const PREFERRED_PAYMENT_KEY = "bepviet_preferred_payment_method_v1";

const outOfStockView = document.getElementById("out-of-stock-view");
const outOfStockMessage = document.getElementById("out-of-stock-message");
const outOfStockItems = document.getElementById("out-of-stock-items");
const btnRemoveUnavailableAndRetry = document.getElementById("btn-remove-unavailable-and-retry");
const savedPaymentBadgeError = document.getElementById("saved-payment-badge-error");

const orderSuccessView = document.getElementById("order-success-view");
const resultOrderCode = document.getElementById("result-order-code");
const resultStatusText = document.getElementById("result-status-text");
const btnCopyOrderCode = document.getElementById("btn-copy-order-code");
const savedPaymentMethodLabel = document.getElementById("saved-payment-method-label");
const btnTrackOrderPage = document.getElementById("btn-track-order-page");
const btnScrollTimeline = document.getElementById("btn-scroll-timeline");
const btnRefreshStatus = document.getElementById("btn-refresh-status");
const statusStepsContainer = document.getElementById("status-steps-container");
const statusHistoryList = document.getElementById("status-history-list");
const resultDeliveryInfo = document.getElementById("result-delivery-info");
const resultItemsList = document.getElementById("result-items-list");
const resultPriceSummary = document.getElementById("result-price-summary");
const resultToast = document.getElementById("result-toast");

const btnDemoSuccess = document.getElementById("btn-demo-success");
const btnDemoOutOfStock = document.getElementById("btn-demo-outofstock");

let currentOrder = null;
let unavailableCartItemIds = [];
let toastTimer = null;

const ORDER_STEPS = [
  { key: "PENDING", label: "Chờ xác nhận", icon: "fa-clock" },
  { key: "CONFIRMED", label: "Đã xác nhận", icon: "fa-circle-check" },
  { key: "PREPARING", label: "Đang chế biến", icon: "fa-fire-burner" },
  { key: "DELIVERING", label: "Đang giao hàng", icon: "fa-motorcycle" },
  { key: "COMPLETED", label: "Hoàn thành", icon: "fa-face-smile" },
];

const STATUS_LABELS = {
  PENDING: "Chờ xác nhận",
  CONFIRMED: "Đã xác nhận",
  PREPARING: "Đang chế biến",
  DELIVERING: "Đang giao hàng",
  COMPLETED: "Hoàn thành",
  CANCELLED: "Đã huỷ",
};

function showResultToast(message, isError = false) {
  resultToast.textContent = message;
  resultToast.classList.remove("hidden", "bg-green-600", "bg-red-600");
  resultToast.classList.add(isError ? "bg-red-600" : "bg-green-600");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => resultToast.classList.add("hidden"), 3200);
}

function getPaymentMethodLabel(method) {
  return method === "BANK_TRANSFER"
    ? "Chuyển khoản ngân hàng"
    : "Thanh toán khi nhận hàng (COD)";
}

function getSavedPaymentMethod() {
  try {
    return localStorage.getItem(PREFERRED_PAYMENT_KEY) || "COD";
  } catch (_) {
    return "COD";
  }
}

function savePaymentMethodPreference(method) {
  if (!method) return;
  try {
    localStorage.setItem(PREFERRED_PAYMENT_KEY, method);
  } catch (_) {
    // ignore storage errors
  }
}

// ── HIỂN THỊ TRẠNG THÁI LỖI KHI MÓN VỪA HẾT HÀNG ──────────────────────────────
async function showOutOfStockErrorView(errorDetail) {
  orderSuccessView.classList.add("hidden");
  outOfStockView.classList.remove("hidden");

  const savedMethod = getSavedPaymentMethod();
  savedPaymentBadgeError.textContent = getPaymentMethodLabel(savedMethod);
  outOfStockMessage.textContent =
    errorDetail ||
    "Món ăn bạn chọn vừa hết hàng trong lúc gửi đơn. Đơn hàng chưa bị trừ tiền và giỏ hàng của bạn vẫn được giữ nguyên.";

  unavailableCartItemIds = [];
  try {
    const cart = await api.get("/carts/me");
    const items = Array.isArray(cart.items) ? cart.items : [];
    const unavailable = items.filter((item) => item.is_available === false);

    if (unavailable.length > 0) {
      unavailableCartItemIds = unavailable.map((i) => i.id);
      btnRemoveUnavailableAndRetry.classList.remove("hidden");
      outOfStockItems.innerHTML = unavailable
        .map(
          (item) => `
          <div class="flex items-center justify-between gap-3 rounded-xl border border-red-200 bg-red-50/70 p-3.5 text-left">
            <div>
              <span class="inline-block rounded bg-red-600 px-2 py-0.5 text-[11px] font-bold text-white">Vừa hết hàng</span>
              <p class="mt-1 font-bold text-gray-900">${escapeHtml(item.dish_name || `Món #${item.dish_id}`)} (x${Number(item.quantity)})</p>
              ${
                (item.warnings || []).length
                  ? `<p class="mt-0.5 text-xs text-red-600">${item.warnings.map(escapeHtml).join(" · ")}</p>`
                  : ""
              }
            </div>
            <span class="text-sm font-bold text-gray-500 line-through">${formatMoney(item.line_total)}</span>
          </div>`,
        )
        .join("");
      return;
    }
  } catch (_) {
    // fallthrough
  }

  btnRemoveUnavailableAndRetry.classList.add("hidden");
  outOfStockItems.innerHTML = `
    <div class="rounded-xl border border-red-200 bg-red-50/60 p-4 text-left text-sm text-red-800">
      <div class="flex items-start gap-3">
        <i class="fa-solid fa-ban mt-0.5 text-red-600" aria-hidden="true"></i>
        <div>
          <strong class="font-bold">Chi tiết từ hệ thống:</strong>
          <p class="mt-1">${escapeHtml(errorDetail || "Món ăn trong đơn vừa hết hàng, không thể đặt đơn.")}</p>
        </div>
      </div>
    </div>`;
}

btnRemoveUnavailableAndRetry.addEventListener("click", async () => {
  if (unavailableCartItemIds.length === 0) return;
  btnRemoveUnavailableAndRetry.disabled = true;
  try {
    for (const itemId of unavailableCartItemIds) {
      await api.delete(`/carts/items/${itemId}`);
    }
    showResultToast("Đã xoá món hết hàng khỏi giỏ. Đang chuyển về trang Thanh toán...");
    setTimeout(() => {
      window.location.href = "checkout.html";
    }, 800);
  } catch (error) {
    btnRemoveUnavailableAndRetry.disabled = false;
    showResultToast(error.message || "Không thể xoá món khỏi giỏ.", true);
  }
});

// ── HIỂN THỊ TRANG ĐẶT MÓN THÀNH CÔNG & THEO DÕI ĐƠN ──────────────────────────
function renderOrderSuccessView(order) {
  currentOrder = order;
  outOfStockView.classList.add("hidden");
  orderSuccessView.classList.remove("hidden");

  if (order.payment_method) {
    savePaymentMethodPreference(order.payment_method);
  }
  const preferredMethod = order.payment_method || getSavedPaymentMethod();
  savedPaymentMethodLabel.textContent = getPaymentMethodLabel(preferredMethod);

  const code = order.order_code || `ORD-${order.id}`;
  resultOrderCode.textContent = code;
  resultStatusText.textContent = STATUS_LABELS[order.status] || order.status || "Chờ xác nhận";

  // Gắn link nút "Theo dõi đơn hàng" truyền kèm order_id sang trang Đơn của tôi
  btnTrackOrderPage.href = `my-orders.html?order_id=${encodeURIComponent(order.id)}`;

  // Nút huỷ đơn chỉ hiển thị khi đơn còn ở trạng thái PENDING (Chờ xác nhận)
  const btnCancelResult = document.getElementById("btn-cancel-order-result");
  if (btnCancelResult) {
    btnCancelResult.classList.toggle("hidden", order.status !== "PENDING");
  }

  renderStatusTimeline(order);
  renderDeliveryAndPaymentInfo(order);
  renderOrderedItemsAndSummary(order);
}

function renderStatusTimeline(order) {
  const currentStatus = order.status || "PENDING";
  if (currentStatus === "CANCELLED") {
    statusStepsContainer.innerHTML = `
      <div class="col-span-5 rounded-xl border border-red-200 bg-red-50 p-4 text-center text-sm font-bold text-red-700">
        <i class="fa-solid fa-circle-xmark mr-1.5" aria-hidden="true"></i>
        Đơn hàng này đã bị huỷ
      </div>`;
  } else {
    const activeIndex = ORDER_STEPS.findIndex((s) => s.key === currentStatus);
    statusStepsContainer.innerHTML = ORDER_STEPS.map((step, idx) => {
      const isDone = idx <= (activeIndex === -1 ? 0 : activeIndex);
      const isCurrent = idx === (activeIndex === -1 ? 0 : activeIndex);
      return `
        <div class="flex flex-col items-center rounded-xl border p-3 text-center transition ${
          isCurrent
            ? "border-orange-500 bg-orange-50 text-orange-700 shadow-sm"
            : isDone
            ? "border-green-200 bg-green-50/60 text-green-700"
            : "border-gray-200 bg-gray-50 text-gray-400"
        }">
          <div class="mb-1.5 flex h-8 w-8 items-center justify-center rounded-full ${
            isCurrent
              ? "bg-orange-600 text-white"
              : isDone
              ? "bg-green-600 text-white"
              : "bg-gray-200 text-gray-500"
          }">
            <i class="fa-solid ${step.icon} text-xs" aria-hidden="true"></i>
          </div>
          <span class="text-xs font-bold">${escapeHtml(step.label)}</span>
        </div>`;
    }).join("");
  }

  const histories = Array.isArray(order.status_history) ? order.status_history : [];
  if (histories.length > 0) {
    statusHistoryList.innerHTML = `
      <strong class="mb-2 block text-gray-700">Lịch sử cập nhật:</strong>
      <ul class="space-y-1.5">
        ${histories
          .map(
            (h) => `
            <li class="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-gray-50 px-3 py-1.5">
              <span>
                <strong class="text-orange-600">${escapeHtml(STATUS_LABELS[h.new_status] || h.new_status)}</strong>
                ${h.note ? ` · ${escapeHtml(h.note)}` : ""}
              </span>
              <span class="text-gray-400">${h.created_at ? formatDateTime(h.created_at) : "Vừa xong"}</span>
            </li>`,
          )
          .join("")}
      </ul>`;
  } else {
    statusHistoryList.innerHTML = `
      <p class="text-gray-500">
        <i class="fa-regular fa-clock mr-1 text-orange-500" aria-hidden="true"></i>
        Đơn hàng vừa được tạo và đang chờ nhà bếp xác nhận.
      </p>`;
  }
}

function renderDeliveryAndPaymentInfo(order) {
  const deliveryTimeText = order.desired_delivery_at
    ? `Hẹn giao lúc ${formatDateTime(order.desired_delivery_at)}`
    : "Giao ngay (30 – 45 phút)";

  resultDeliveryInfo.innerHTML = `
    <div class="flex justify-between gap-3 border-b border-gray-100 pb-2.5">
      <dt class="text-gray-500">Người nhận:</dt>
      <dd class="text-right font-bold text-gray-900">${escapeHtml(order.recipient_name)}</dd>
    </div>
    <div class="flex justify-between gap-3 border-b border-gray-100 pb-2.5">
      <dt class="text-gray-500">Số điện thoại:</dt>
      <dd class="text-right font-semibold text-gray-800">${escapeHtml(order.recipient_phone)}</dd>
    </div>
    <div class="flex justify-between gap-3 border-b border-gray-100 pb-2.5">
      <dt class="text-gray-500">Địa chỉ giao:</dt>
      <dd class="text-right font-medium text-gray-800">${escapeHtml(order.delivery_address)}</dd>
    </div>
    <div class="flex justify-between gap-3 border-b border-gray-100 pb-2.5">
      <dt class="text-gray-500">Thời gian giao:</dt>
      <dd class="text-right font-medium text-gray-800">${escapeHtml(deliveryTimeText)}</dd>
    </div>
    <div class="flex justify-between gap-3">
      <dt class="text-gray-500">Thanh toán:</dt>
      <dd class="text-right font-bold text-emerald-700">${escapeHtml(getPaymentMethodLabel(order.payment_method))}</dd>
    </div>`;
}

function renderOrderedItemsAndSummary(order) {
  const items = Array.isArray(order.items) ? order.items : [];
  if (items.length === 0) {
    resultItemsList.innerHTML = `<p class="text-gray-400">Không có dữ liệu món ăn.</p>`;
  } else {
    resultItemsList.innerHTML = items
      .map((item) => {
        const opts = (item.selected_options || [])
          .map((o) => `${escapeHtml(o.name || `Tùy chọn #${o.option_id}`)}${Number(o.price) > 0 ? ` (+${formatMoney(o.price)})` : ""}`)
          .join(", ");
        return `
          <div class="flex items-start justify-between gap-3 border-b border-gray-100 pb-2.5 last:border-b-0">
            <div>
              <p class="font-bold text-gray-900">
                <span class="text-orange-600">${Number(item.quantity)}x</span>
                ${escapeHtml(item.dish_name || `Món #${item.dish_id}`)}
              </p>
              ${opts ? `<p class="text-xs text-gray-500">${opts}</p>` : ""}
              ${item.note ? `<p class="text-xs italic text-gray-400">Ghi chú: ${escapeHtml(item.note)}</p>` : ""}
            </div>
            <strong class="shrink-0 text-gray-900">${formatMoney(item.line_total)}</strong>
          </div>`;
      })
      .join("");
  }

  const discount = Number(order.discount_amount || 0);
  resultPriceSummary.innerHTML = `
    <div class="flex justify-between text-gray-600">
      <dt>Tạm tính</dt>
      <dd class="font-semibold">${formatMoney(order.subtotal || 0)}</dd>
    </div>
    <div class="flex justify-between text-gray-600">
      <dt>Phí giao hàng</dt>
      <dd class="font-semibold">${formatMoney(order.shipping_fee || 0)}</dd>
    </div>
    ${
      discount > 0
        ? `<div class="flex justify-between text-green-700">
            <dt>Giảm giá</dt>
            <dd class="font-bold">-${formatMoney(discount)}</dd>
          </div>`
        : ""
    }
    <div class="flex justify-between border-t border-dashed border-gray-200 pt-2.5 text-base">
      <strong class="text-gray-900">Tổng thanh toán</strong>
      <strong class="text-xl font-extrabold text-orange-600">${formatMoney(order.total_amount || 0)}</strong>
    </div>`;
}

// ── SỰ KIỆN NÚT SAO CHÉP MÃ ĐƠN & THEO DÕI TIẾN TRÌNH ────────────────────────
btnCopyOrderCode.addEventListener("click", async () => {
  const code = resultOrderCode.textContent.trim();
  if (!code) return;
  try {
    await navigator.clipboard.writeText(code);
    showResultToast(`Đã sao chép mã đơn ${code}!`);
  } catch (_) {
    showResultToast(`Mã đơn của bạn: ${code}`);
  }
});

btnScrollTimeline.addEventListener("click", () => {
  document.getElementById("order-tracking-section").scrollIntoView({
    behavior: "smooth",
    block: "start",
  });
});

btnRefreshStatus.addEventListener("click", async () => {
  if (!currentOrder?.id) return;
  btnRefreshStatus.disabled = true;
  try {
    const freshOrder = await api.get(`/orders/my-orders/${currentOrder.id}`);
    try {
      sessionStorage.setItem(LAST_ORDER_STORAGE_KEY, JSON.stringify(freshOrder));
    } catch (_) {}
    renderOrderSuccessView(freshOrder);
    showResultToast("Đã cập nhật trạng thái đơn hàng mới nhất!");
  } catch (error) {
    showResultToast(error.message || "Không thể làm mới trạng thái đơn.", true);
  } finally {
    btnRefreshStatus.disabled = false;
  }
});

// Nút chuyển nhanh 2 chế độ để demo / chấm bài
btnDemoSuccess.addEventListener("click", () => {
  if (currentOrder) {
    renderOrderSuccessView(currentOrder);
  } else {
    initOrderResultPage(true);
  }
});

btnDemoOutOfStock.addEventListener("click", () => {
  showOutOfStockErrorView("Món ăn 'Cơm gà xối mỡ (Hết hàng)' vừa hết hàng trong lúc đặt, không thể tạo đơn.");
});

// ── KHỞI TẠO TRANG KẾT QUẢ ĐẶT MÓN ──────────────────────────────────────────
async function initOrderResultPage(forceSuccess = false) {
  const params = new URLSearchParams(window.location.search);
  const statusParam = params.get("status");
  const orderIdParam = params.get("order_id");
  const errorMsgParam = params.get("message");

  // 1. Nếu chuyển sang với trạng thái lỗi món vừa hết hàng
  if (!forceSuccess && statusParam === "out_of_stock") {
    let savedErr = errorMsgParam;
    if (!savedErr) {
      try {
        savedErr = sessionStorage.getItem(LAST_ORDER_ERROR_KEY);
      } catch (_) {}
    }
    await showOutOfStockErrorView(savedErr);
    return;
  }

  // 2. Nếu có order_id trên URL -> tải trực tiếp từ API
  if (orderIdParam) {
    try {
      const order = await api.get(`/orders/my-orders/${encodeURIComponent(orderIdParam)}`);
      renderOrderSuccessView(order);
      return;
    } catch (_) {
      // Fallback xuống sessionStorage nếu gọi API lỗi
    }
  }

  // 3. Thử đọc đơn vừa đặt từ sessionStorage
  try {
    const cached = sessionStorage.getItem(LAST_ORDER_STORAGE_KEY);
    if (cached) {
      const parsed = JSON.parse(cached);
      if (parsed && parsed.id) {
        renderOrderSuccessView(parsed);
        return;
      }
    }
  } catch (_) {}

  // 4. Nếu mở trực tiếp order-result.html -> lấy đơn hàng gần nhất của user từ /api/orders/my-orders
  try {
    const myOrders = await api.get("/orders/my-orders");
    if (Array.isArray(myOrders) && myOrders.length > 0) {
      renderOrderSuccessView(myOrders[0]);
      return;
    }
  } catch (_) {}

  // 5. Fallback dữ liệu mẫu để giao diện luôn hiển thị đầy đủ khi mở trực tiếp
  renderOrderSuccessView({
    id: 1,
    order_code: "ORD-261124-DEMO",
    status: "PENDING",
    recipient_name: "Thái Nguyễn Gia Bảo",
    recipient_phone: "0901234567",
    delivery_address: "123 Nguyễn Trãi, Phường Mộ Lao, Quận Hà Đông",
    delivery_area_id: 1,
    payment_method: getSavedPaymentMethod(),
    desired_delivery_at: null,
    subtotal: 124000,
    shipping_fee: 15000,
    discount_amount: 12400,
    total_amount: 126600,
    items: [
      {
        dish_id: 1,
        dish_name: "Mì trộn Indomie đặc biệt",
        quantity: 2,
        selected_options: [
          { option_id: 1, name: "Thêm trứng lòng đào", price: 7000 },
          { option_id: 2, name: "Thêm phô mai kéo sợi", price: 10000 },
        ],
        note: "ít cay",
        line_total: 124000,
      },
    ],
    status_history: [
      {
        new_status: "PENDING",
        note: "Khách hàng tạo đơn hàng (Chờ xác nhận)",
        created_at: new Date().toISOString(),
      },
    ],
  });
}

initOrderResultPage();

// Tự động cập nhật trạng thái đơn mỗi 15 giây
setInterval(async () => {
  if (!currentOrder?.id) return;
  try {
    const fresh = await api.get(`/orders/my-orders/${currentOrder.id}`);
    renderOrderSuccessView(fresh);
  } catch (_) {}
}, 15000);

const btnCancelOrderResult = document.getElementById("btn-cancel-order-result");
if (btnCancelOrderResult) {
  btnCancelOrderResult.addEventListener("click", async () => {
    if (!currentOrder?.id) return;
    const reason = window.prompt("Nhập lý do huỷ đơn hàng:", "Đổi ý / Muốn đổi món");
    if (reason === null || !reason.trim()) return;
    try {
      const updated = await api.post(`/orders/${currentOrder.id}/cancel`, {
        reason: reason.trim(),
        user_id: currentOrder.user_id || 1,
        role: "CUSTOMER",
      });
      renderOrderSuccessView(updated);
      showResultToast("Đã huỷ đơn hàng thành công!");
    } catch (error) {
      showResultToast(error.message || "Không thể huỷ đơn hàng.", true);
    }
  });
}

