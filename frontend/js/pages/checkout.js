// Logic trang Thanh toán (Checkout):
// - Chọn địa chỉ từ sổ địa chỉ (lưu localStorage + đồng bộ khu vực giao hàng từ /api/delivery-areas)
// - Chọn giờ giao (Giao ngay hoặc Hẹn giờ trong khung mở cửa 07:00 - 23:00)
// - Nhập & kiểm tra mã giảm giá qua server (/api/carts/calculate)
// - Chọn phương thức thanh toán (mặc định COD)
// - Hiển thị tóm tắt đơn, phí ship theo khu vực, giảm giá, tổng thanh toán & cảnh báo món hết/đổi giá
// - Đặt món qua /api/orders/checkout (chống bấm 2 lần bằng X-Idempotency-Key & khóa nút) và báo lỗi rõ ràng

const ADDRESS_BOOK_KEY = "bepviet_address_book_v1";
const PREFERRED_PAYMENT_KEY = "bepviet_preferred_payment_method_v1";
const LAST_ORDER_STORAGE_KEY = "bepviet_last_order_v1";
const LAST_ORDER_ERROR_KEY = "bepviet_last_order_error_v1";
const STORE_OPEN_MINUTES = 7 * 60;   // 07:00
const STORE_CLOSE_MINUTES = 23 * 60; // 23:00

// DOM Elements
const checkoutForm = document.getElementById("checkout-form");
const addressBookList = document.getElementById("address-book-list");
const recipientNameInput = document.getElementById("recipient-name");
const recipientPhoneInput = document.getElementById("recipient-phone");
const deliveryAreaSelect = document.getElementById("delivery-area");
const addressLabelInput = document.getElementById("address-label");
const deliveryAddressInput = document.getElementById("delivery-address");
const btnSaveAddress = document.getElementById("btn-save-address");
const btnToggleNewAddress = document.getElementById("btn-toggle-new-address");

const cardDeliveryNow = document.getElementById("card-delivery-now");
const cardDeliveryScheduled = document.getElementById("card-delivery-scheduled");
const scheduledTimeBox = document.getElementById("scheduled-time-box");
const desiredDeliveryInput = document.getElementById("desired-delivery-at");

const cardPaymentCod = document.getElementById("card-payment-cod");
const cardPaymentBank = document.getElementById("card-payment-bank");

const voucherInput = document.getElementById("voucher-code");
const btnApplyVoucher = document.getElementById("btn-apply-voucher");
const btnRemoveVoucher = document.getElementById("btn-remove-voucher");
const voucherFeedback = document.getElementById("voucher-feedback");

const checkoutItemsList = document.getElementById("checkout-items-list");
const summaryTotalQty = document.getElementById("summary-total-qty");
const summarySubtotal = document.getElementById("summary-subtotal");
const summaryAreaName = document.getElementById("summary-area-name");
const summaryShipping = document.getElementById("summary-shipping");
const summaryDiscountRow = document.getElementById("summary-discount-row");
const summaryVoucherLabel = document.getElementById("summary-voucher-label");
const summaryDiscount = document.getElementById("summary-discount");
const summaryTotal = document.getElementById("summary-total");
const btnPlaceOrder = document.getElementById("btn-place-order");

const errorBanner = document.getElementById("checkout-error-banner");
const errorList = document.getElementById("checkout-error-list");
const serverWarningBanner = document.getElementById("server-warning-banner");
const serverWarningList = document.getElementById("server-warning-list");
const checkoutToast = document.getElementById("checkout-toast");
const orderSuccessModal = document.getElementById("order-success-modal");

// State
let deliveryAreas = [];
let addressBook = [];
let selectedAddressId = null;
let currentCart = null;
let appliedVoucherCode = null;
let isSubmittingOrder = false;
let toastTimer = null;

function showCheckoutToast(message, isError = false) {
  checkoutToast.textContent = message;
  checkoutToast.classList.remove("hidden", "bg-green-600", "bg-red-600");
  checkoutToast.classList.add(isError ? "bg-red-600" : "bg-green-600");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => checkoutToast.classList.add("hidden"), 3500);
}

function getDishImageUrl(imageUrl) {
  if (!imageUrl) return "../assets/images/logo.svg";
  if (imageUrl.startsWith("/uploads/")) {
    return `${CONFIG.API_BASE_URL.replace(/\/api\/?$/, "")}${imageUrl}`;
  }
  return imageUrl;
}

// ── 1. QUẢN LÝ SỔ ĐỊA CHỈ ────────────────────────────────────────────────────
function getDefaultAddresses(areas) {
  const area1 = areas[0]?.id || 1;
  const area2 = areas[1]?.id || area1;
  return [
    {
      id: "addr_default_1",
      label: "Nhà riêng",
      recipient_name: "Thái Nguyễn Gia Bảo",
      recipient_phone: "0901234567",
      delivery_area_id: area1,
      delivery_address: "123 Nguyễn Trãi, Phường Mộ Lao, Quận Hà Đông",
    },
    {
      id: "addr_default_2",
      label: "Trường học / Văn phòng",
      recipient_name: "Thái Nguyễn Gia Bảo",
      recipient_phone: "0901234567",
      delivery_area_id: area2,
      delivery_address: "Km10 Nguyễn Trãi, Quận Thanh Xuân",
    },
  ];
}

function loadAddressBook(areas) {
  try {
    const raw = localStorage.getItem(ADDRESS_BOOK_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed) && parsed.length > 0) {
        addressBook = parsed;
        return;
      }
    }
  } catch (_) {
    // ignore storage errors
  }
  addressBook = getDefaultAddresses(areas);
  saveAddressBook();
}

function saveAddressBook() {
  try {
    localStorage.setItem(ADDRESS_BOOK_KEY, JSON.stringify(addressBook));
  } catch (_) {
    // ignore storage errors
  }
}

function getAreaById(areaId) {
  return deliveryAreas.find((a) => Number(a.id) === Number(areaId)) || null;
}

function renderAddressBook() {
  if (addressBook.length === 0) {
    addressBookList.innerHTML = `
      <p class="col-span-2 rounded-xl border border-dashed border-gray-200 p-3 text-center text-xs text-gray-400">
        Sổ địa chỉ đang trống. Điền thông tin bên dưới và bấm "Lưu sổ" để lưu lại.
      </p>`;
    return;
  }

  addressBookList.innerHTML = addressBook
    .map((addr) => {
      const isSelected = addr.id === selectedAddressId;
      const area = getAreaById(addr.delivery_area_id);
      const areaText = area
        ? `${area.name} (+${formatMoney(area.shipping_fee)})`
        : `Khu vực #${addr.delivery_area_id}`;

      return `
        <div
          data-address-id="${escapeHtml(addr.id)}"
          class="group relative cursor-pointer rounded-xl border-2 p-3.5 transition ${
            isSelected
              ? "border-orange-500 bg-orange-50/50"
              : "border-gray-200 bg-white hover:border-gray-300"
          }">
          <div class="flex items-center justify-between gap-2">
            <span class="inline-flex items-center gap-1.5 rounded-full bg-orange-100 px-2.5 py-0.5 text-xs font-bold text-orange-700">
              <i class="fa-solid fa-location-dot" aria-hidden="true"></i>
              ${escapeHtml(addr.label || "Địa chỉ đã lưu")}
            </span>
            ${
              addressBook.length > 1
                ? `<button
                    type="button"
                    data-delete-address="${escapeHtml(addr.id)}"
                    title="Xoá khỏi sổ địa chỉ"
                    class="rounded p-1 text-xs text-gray-400 hover:bg-red-50 hover:text-red-600">
                    <i class="fa-regular fa-trash-can" aria-hidden="true"></i>
                  </button>`
                : ""
            }
          </div>
          <p class="mt-2 text-sm font-bold text-gray-900">
            ${escapeHtml(addr.recipient_name)} · <span class="font-semibold text-gray-600">${escapeHtml(addr.recipient_phone)}</span>
          </p>
          <p class="mt-0.5 line-clamp-2 text-xs text-gray-600">${escapeHtml(addr.delivery_address)}</p>
          <p class="mt-1 text-xs font-semibold text-orange-600">${escapeHtml(areaText)}</p>
        </div>`;
    })
    .join("");
}

async function selectAddressFromBook(addressId, shouldRecalculate = true) {
  const found = addressBook.find((a) => a.id === addressId);
  if (!found) return;

  selectedAddressId = found.id;
  recipientNameInput.value = found.recipient_name || "";
  recipientPhoneInput.value = found.recipient_phone || "";
  deliveryAreaSelect.value = String(found.delivery_area_id || "");
  addressLabelInput.value = found.label || "";
  deliveryAddressInput.value = found.delivery_address || "";

  clearFieldErrors();
  renderAddressBook();

  if (shouldRecalculate) {
    await recalculateCartFromServer();
  }
}

addressBookList.addEventListener("click", async (event) => {
  const deleteBtn = event.target.closest("button[data-delete-address]");
  if (deleteBtn) {
    event.stopPropagation();
    const idToDelete = deleteBtn.dataset.deleteAddress;
    addressBook = addressBook.filter((a) => a.id !== idToDelete);
    saveAddressBook();
    if (selectedAddressId === idToDelete) {
      selectedAddressId = addressBook[0]?.id || null;
      if (selectedAddressId) {
        await selectAddressFromBook(selectedAddressId, true);
        return;
      }
    }
    renderAddressBook();
    showCheckoutToast("Đã xoá địa chỉ khỏi sổ địa chỉ.");
    return;
  }

  const card = event.target.closest("div[data-address-id]");
  if (card) {
    await selectAddressFromBook(card.dataset.addressId, true);
  }
});

btnToggleNewAddress.addEventListener("click", () => {
  selectedAddressId = null;
  addressLabelInput.value = "";
  deliveryAddressInput.value = "";
  renderAddressBook();
  addressLabelInput.focus();
  showCheckoutToast("Nhập thông tin địa chỉ mới rồi bấm 'Lưu sổ'.");
});

btnSaveAddress.addEventListener("click", () => {
  const name = recipientNameInput.value.trim();
  const phone = recipientPhoneInput.value.trim();
  const areaId = Number(deliveryAreaSelect.value);
  const address = deliveryAddressInput.value.trim();
  const label = addressLabelInput.value.trim() || `Địa chỉ ${addressBook.length + 1}`;

  if (!name || !phone || !areaId || !address) {
    showCheckoutToast("Vui lòng điền đủ Họ tên, SĐT, Khu vực và Địa chỉ trước khi lưu vào sổ.", true);
    return;
  }

  const newAddr = {
    id: `addr_${Date.now()}`,
    label,
    recipient_name: name,
    recipient_phone: phone,
    delivery_area_id: areaId,
    delivery_address: address,
  };
  addressBook.unshift(newAddr);
  selectedAddressId = newAddr.id;
  saveAddressBook();
  renderAddressBook();
  showCheckoutToast(`Đã lưu "${label}" vào sổ địa chỉ!`);
});

// Khi người dùng đổi Khu vực giao hàng -> Tính lại phí ship & tổng tiền từ server ngay
deliveryAreaSelect.addEventListener("change", async () => {
  clearFieldError("err-delivery-area", deliveryAreaSelect);
  await recalculateCartFromServer();
});

// ── 2. GIỜ GIAO HÀNG (GIAO NGAY / HẸN GIỜ) ───────────────────────────────────
function setDefaultScheduledTime() {
  const now = new Date();
  now.setMinutes(now.getMinutes() + 45);
  const yyyy = now.getFullYear();
  const mm = String(now.getMonth() + 1).padStart(2, "0");
  const dd = String(now.getDate()).padStart(2, "0");
  let hh = now.getHours();
  let min = now.getMinutes();
  if (hh < 7) {
    hh = 7;
    min = 30;
  } else if (hh >= 23) {
    hh = 22;
    min = 30;
  }
  desiredDeliveryInput.value = `${yyyy}-${mm}-${dd}T${String(hh).padStart(2, "0")}:${String(min).padStart(2, "0")}`;
}

function getSelectedDeliveryMode() {
  const checked = document.querySelector('input[name="delivery_time_mode"]:checked');
  return checked ? checked.value : "NOW";
}

function updateDeliveryModeUI() {
  const mode = getSelectedDeliveryMode();
  const isScheduled = mode === "SCHEDULED";

  scheduledTimeBox.classList.toggle("hidden", !isScheduled);
  cardDeliveryNow.className = `flex cursor-pointer items-start gap-3 rounded-xl border-2 p-4 transition ${
    !isScheduled ? "border-orange-500 bg-orange-50/40" : "border-gray-200 bg-white hover:border-gray-300"
  }`;
  cardDeliveryScheduled.className = `flex cursor-pointer items-start gap-3 rounded-xl border-2 p-4 transition ${
    isScheduled ? "border-orange-500 bg-orange-50/40" : "border-gray-200 bg-white hover:border-gray-300"
  }`;

  if (isScheduled && !desiredDeliveryInput.value) {
    setDefaultScheduledTime();
  }
  clearFieldError("err-desired-delivery", desiredDeliveryInput);
}

document.querySelectorAll('input[name="delivery_time_mode"]').forEach((radio) => {
  radio.addEventListener("change", updateDeliveryModeUI);
});

desiredDeliveryInput.addEventListener("change", () => {
  validateScheduledTime(true);
});

function validateScheduledTime(showInline = true) {
  if (getSelectedDeliveryMode() !== "SCHEDULED") {
    clearFieldError("err-desired-delivery", desiredDeliveryInput);
    return null;
  }

  const val = desiredDeliveryInput.value;
  if (!val) {
    const msg = "Vui lòng chọn ngày và giờ muốn nhận hàng.";
    if (showInline) showFieldError("err-desired-delivery", desiredDeliveryInput, msg);
    return msg;
  }

  const chosen = new Date(val);
  if (Number.isNaN(chosen.getTime())) {
    const msg = "Thời gian hẹn giao không hợp lệ.";
    if (showInline) showFieldError("err-desired-delivery", desiredDeliveryInput, msg);
    return msg;
  }

  const totalMinutes = chosen.getHours() * 60 + chosen.getMinutes();
  if (totalMinutes < STORE_OPEN_MINUTES || totalMinutes > STORE_CLOSE_MINUTES) {
    const hhmm = `${String(chosen.getHours()).padStart(2, "0")}:${String(chosen.getMinutes()).padStart(2, "0")}`;
    const msg = `Giờ giao mong muốn (${hhmm}) nằm ngoài giờ mở cửa của quán (07:00 - 23:00).`;
    if (showInline) showFieldError("err-desired-delivery", desiredDeliveryInput, msg);
    return msg;
  }

  clearFieldError("err-desired-delivery", desiredDeliveryInput);
  return null;
}

// ── 3. PHƯƠNG THỨC THANH TOÁN (COD / BANK_TRANSFER - LƯU LỰA CHỌN CHO LẦN SAU) ──
function getSelectedPaymentMethod() {
  const checked = document.querySelector('input[name="payment_method"]:checked');
  return checked ? checked.value : "COD";
}

function updatePaymentMethodCards(selectedMethod) {
  const isCod = selectedMethod === "COD";
  cardPaymentCod.className = `flex cursor-pointer items-start gap-3 rounded-xl border-2 p-4 transition ${
    isCod ? "border-orange-500 bg-orange-50/40" : "border-gray-200 bg-white hover:border-gray-300"
  }`;
  cardPaymentBank.className = `flex cursor-pointer items-start gap-3 rounded-xl border-2 p-4 transition ${
    !isCod ? "border-orange-500 bg-orange-50/40" : "border-gray-200 bg-white hover:border-gray-300"
  }`;
}

function savePreferredPaymentMethod(method) {
  try {
    localStorage.setItem(PREFERRED_PAYMENT_KEY, method);
  } catch (_) {}
  const hint = document.getElementById("saved-payment-hint");
  if (hint) {
    const label = method === "BANK_TRANSFER" ? "Chuyển khoản" : "COD";
    hint.innerHTML = `<i class="fa-solid fa-circle-check" aria-hidden="true"></i> Đã lưu lựa chọn (${label}) cho lần sau`;
  }
}

function restorePreferredPaymentMethod() {
  let saved = "COD";
  try {
    saved = localStorage.getItem(PREFERRED_PAYMENT_KEY) || "COD";
  } catch (_) {}
  if (saved !== "COD" && saved !== "BANK_TRANSFER") saved = "COD";

  const targetRadio = document.querySelector(`input[name="payment_method"][value="${saved}"]`);
  if (targetRadio) {
    targetRadio.checked = true;
  }
  updatePaymentMethodCards(saved);
  const hint = document.getElementById("saved-payment-hint");
  if (hint) {
    const label = saved === "BANK_TRANSFER" ? "Chuyển khoản" : "COD";
    hint.innerHTML = `<i class="fa-solid fa-bookmark" aria-hidden="true"></i> Đã nhớ lựa chọn (${label}) từ lần trước`;
  }
}

document.querySelectorAll('input[name="payment_method"]').forEach((radio) => {
  radio.addEventListener("change", () => {
    const method = getSelectedPaymentMethod();
    updatePaymentMethodCards(method);
    savePreferredPaymentMethod(method);
  });
});

// ── 4. MÃ GIẢM GIÁ (VOUCHER / COUPON) ────────────────────────────────────────
function setVoucherFeedback(message, isError = false) {
  if (!message) {
    voucherFeedback.classList.add("hidden");
    voucherFeedback.textContent = "";
    return;
  }
  voucherFeedback.textContent = message;
  voucherFeedback.classList.remove("hidden", "text-green-600", "text-red-600");
  voucherFeedback.classList.add(isError ? "text-red-600" : "text-green-600");
}

async function applyVoucherCode(codeToApply) {
  const code = (codeToApply ?? voucherInput.value).trim().toUpperCase();
  if (!code) {
    setVoucherFeedback("Vui lòng nhập mã giảm giá trước khi bấm Áp dụng.", true);
    return;
  }

  voucherInput.value = code;
  btnApplyVoucher.disabled = true;
  try {
    const areaId = deliveryAreaSelect.value ? Number(deliveryAreaSelect.value) : null;
    const calculated = await api.post("/carts/calculate", {
      delivery_area_id: areaId,
      voucher_code: code,
    });
    currentCart = calculated;
    appliedVoucherCode = calculated.voucher_code || code;
    btnRemoveVoucher.classList.remove("hidden");
    renderOrderSummary(currentCart);
    setVoucherFeedback(
      `Áp dụng mã ${appliedVoucherCode} thành công! Giảm ${formatMoney(calculated.discount_amount)}.`,
      false,
    );
    showCheckoutToast(`Đã áp dụng mã giảm giá ${appliedVoucherCode}!`);
  } catch (error) {
    appliedVoucherCode = null;
    btnRemoveVoucher.classList.add("hidden");
    setVoucherFeedback(error.message || "Mã giảm giá không hợp lệ.", true);
    await recalculateCartFromServer(null);
  } finally {
    btnApplyVoucher.disabled = false;
  }
}

btnApplyVoucher.addEventListener("click", () => applyVoucherCode());

btnRemoveVoucher.addEventListener("click", async () => {
  appliedVoucherCode = null;
  voucherInput.value = "";
  btnRemoveVoucher.classList.add("hidden");
  setVoucherFeedback("");
  await recalculateCartFromServer(null);
  showCheckoutToast("Đã gỡ mã giảm giá.");
});

document.querySelectorAll("button[data-voucher]").forEach((btn) => {
  btn.addEventListener("click", () => {
    voucherInput.value = btn.dataset.voucher;
    applyVoucherCode(btn.dataset.voucher);
  });
});

// ── 5. TÍNH TIỀN & HIỂN THỊ TÓM TẮT ĐƠN HÀNG TỪ SERVER ───────────────────────
async function recalculateCartFromServer(overrideVoucher = undefined) {
  const areaId = deliveryAreaSelect.value ? Number(deliveryAreaSelect.value) : null;
  const voucher = overrideVoucher !== undefined ? overrideVoucher : appliedVoucherCode;

  try {
    currentCart = await api.post("/carts/calculate", {
      delivery_area_id: areaId,
      voucher_code: voucher,
    });
    renderOrderSummary(currentCart);
  } catch (error) {
    // Nếu lỗi do mã giảm giá không còn đủ điều kiện khi đổi món/khu vực -> gỡ mã và tính lại
    if (voucher) {
      appliedVoucherCode = null;
      btnRemoveVoucher.classList.add("hidden");
      setVoucherFeedback(error.message, true);
      try {
        currentCart = await api.post("/carts/calculate", {
          delivery_area_id: areaId,
          voucher_code: null,
        });
        renderOrderSummary(currentCart);
        return;
      } catch (_) {
        // fallthrough
      }
    }
    showCheckoutToast(error.message || "Không thể tính tiền đơn hàng.", true);
  }
}

function renderOrderSummary(cart) {
  const items = Array.isArray(cart?.items) ? cart.items : [];

  if (items.length === 0) {
    checkoutItemsList.innerHTML = `
      <div class="rounded-xl border border-dashed border-gray-200 p-6 text-center">
        <p class="font-semibold text-gray-700">Giỏ hàng của bạn đang trống</p>
        <p class="mt-1 text-xs text-gray-500">Vui lòng chọn món ăn trước khi thanh toán.</p>
        <a href="menu.html" class="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-orange-600 px-3.5 py-2 text-xs font-bold text-white hover:bg-orange-700">
          <i class="fa-solid fa-utensils" aria-hidden="true"></i>
          Đi tới Thực đơn
        </a>
      </div>`;
  } else {
    checkoutItemsList.innerHTML = items
      .map((item) => {
        const opts = (item.selected_options || [])
          .map((o) => `${escapeHtml(o.name || `Tùy chọn #${o.option_id}`)}${Number(o.price) > 0 ? ` (+${formatMoney(o.price)})` : ""}`)
          .join(", ");
        const itemWarn = (item.warnings || []).length
          ? `<p class="mt-1 text-xs font-semibold text-red-600">${item.warnings.map(escapeHtml).join(" · ")}</p>`
          : "";

        return `
          <div class="flex items-start justify-between gap-3 border-b border-gray-100 pb-3 last:border-b-0 last:pb-0">
            <img
              src="${escapeHtml(getDishImageUrl(item.dish_image_url))}"
              alt="${escapeHtml(item.dish_name || "Món ăn")}"
              class="h-12 w-12 shrink-0 rounded-lg bg-gray-100 object-cover"
              onerror="this.onerror=null;this.src='../assets/images/logo.svg'">
            <div class="min-w-0 flex-1">
              <div class="flex items-start justify-between gap-2">
                <p class="truncate font-bold text-gray-900">
                  <span class="text-orange-600">${Number(item.quantity)}x</span>
                  ${escapeHtml(item.dish_name || `Món #${item.dish_id}`)}
                </p>
                <span class="shrink-0 font-bold text-gray-900">${formatMoney(item.line_total)}</span>
              </div>
              ${opts ? `<p class="mt-0.5 text-xs text-gray-500">${opts}</p>` : ""}
              ${item.note ? `<p class="mt-0.5 text-xs italic text-gray-400">Ghi chú: ${escapeHtml(item.note)}</p>` : ""}
              ${itemWarn}
            </div>
          </div>`;
      })
      .join("");
  }

  // Cảnh báo từ server (món hết hàng / đổi giá)
  const warnings = Array.isArray(cart?.warnings) ? cart.warnings : [];
  if (warnings.length > 0) {
    serverWarningList.innerHTML = warnings.map((w) => `<li>${escapeHtml(w)}</li>`).join("");
    serverWarningBanner.classList.remove("hidden");
  } else {
    serverWarningBanner.classList.add("hidden");
  }

  // Số liệu tổng kết
  summaryTotalQty.textContent = String(cart?.total_quantity || 0);
  summarySubtotal.textContent = formatMoney(cart?.subtotal || 0);

  const selectedArea = getAreaById(deliveryAreaSelect.value);
  summaryAreaName.textContent = selectedArea ? selectedArea.name : "Chưa chọn khu vực";
  summaryShipping.textContent = selectedArea ? formatMoney(cart?.shipping_fee || 0) : "Chọn khu vực";

  const discountAmt = Number(cart?.discount_amount || 0);
  if (discountAmt > 0) {
    summaryDiscountRow.classList.remove("hidden");
    summaryVoucherLabel.textContent = cart?.voucher_code || appliedVoucherCode || "";
    summaryDiscount.textContent = `-${formatMoney(discountAmt)}`;
  } else {
    summaryDiscountRow.classList.add("hidden");
  }

  summaryTotal.textContent = formatMoney(cart?.total_amount || 0);

  // Khoá nút Đặt món nếu giỏ trống hoặc có món đã hết hàng
  const cannotCheckout = items.length === 0 || cart?.has_unavailable_items === true;
  btnPlaceOrder.disabled = cannotCheckout || isSubmittingOrder;
  if (cart?.has_unavailable_items) {
    btnPlaceOrder.innerHTML = `<i class="fa-solid fa-ban" aria-hidden="true"></i><span>Có món đã hết hàng (Vui lòng sửa giỏ)</span>`;
  } else {
    btnPlaceOrder.innerHTML = `<i class="fa-solid fa-check-circle" aria-hidden="true"></i><span>Đặt món · ${formatMoney(cart?.total_amount || 0)}</span>`;
  }
}

// ── 6. VALIDATION & BÁO LỖI RÕ RÀNG ──────────────────────────────────────────
function showFieldError(errorId, inputEl, message) {
  const errEl = document.getElementById(errorId);
  if (errEl) {
    errEl.textContent = message;
    errEl.classList.remove("hidden");
  }
  if (inputEl) {
    inputEl.classList.add("border-red-500", "ring-1", "ring-red-300");
  }
}

function clearFieldError(errorId, inputEl) {
  const errEl = document.getElementById(errorId);
  if (errEl) {
    errEl.textContent = "";
    errEl.classList.add("hidden");
  }
  if (inputEl) {
    inputEl.classList.remove("border-red-500", "ring-1", "ring-red-300");
  }
}

function clearFieldErrors() {
  clearFieldError("err-recipient-name", recipientNameInput);
  clearFieldError("err-recipient-phone", recipientPhoneInput);
  clearFieldError("err-delivery-area", deliveryAreaSelect);
  clearFieldError("err-delivery-address", deliveryAddressInput);
  clearFieldError("err-desired-delivery", desiredDeliveryInput);
  errorBanner.classList.add("hidden");
  errorList.innerHTML = "";
}

function showErrorBanner(messages) {
  if (!messages || messages.length === 0) {
    errorBanner.classList.add("hidden");
    return;
  }
  errorList.innerHTML = messages.map((m) => `<li>${escapeHtml(m)}</li>`).join("");
  errorBanner.classList.remove("hidden");
  errorBanner.scrollIntoView({ behavior: "smooth", block: "center" });
}

function validateCheckoutForm() {
  clearFieldErrors();
  const errors = [];

  if (!currentCart || !Array.isArray(currentCart.items) || currentCart.items.length === 0) {
    errors.push("Giỏ hàng của bạn đang trống. Vui lòng thêm món ăn trước khi đặt đơn.");
  } else if (currentCart.has_unavailable_items) {
    errors.push("Trong giỏ hàng có món đã hết hoặc ngừng bán. Vui lòng quay lại giỏ hàng để xoá món hết.");
  }

  const name = recipientNameInput.value.trim();
  if (!name) {
    const msg = "Vui lòng nhập họ và tên người nhận.";
    showFieldError("err-recipient-name", recipientNameInput, msg);
    errors.push(msg);
  }

  const phone = recipientPhoneInput.value.trim();
  const phoneRegex = /^(0|\+84)[0-9]{8,10}$/;
  if (!phone) {
    const msg = "Vui lòng nhập số điện thoại liên hệ.";
    showFieldError("err-recipient-phone", recipientPhoneInput, msg);
    errors.push(msg);
  } else if (!phoneRegex.test(phone.replace(/\s+/g, ""))) {
    const msg = "Số điện thoại không đúng định dạng (VD: 0901234567).";
    showFieldError("err-recipient-phone", recipientPhoneInput, msg);
    errors.push(msg);
  }

  const areaId = Number(deliveryAreaSelect.value);
  if (!areaId) {
    const msg = "Vui lòng chọn khu vực giao hàng để tính phí ship.";
    showFieldError("err-delivery-area", deliveryAreaSelect, msg);
    errors.push(msg);
  }

  const address = deliveryAddressInput.value.trim();
  if (!address || address.length < 5) {
    const msg = "Vui lòng nhập địa chỉ nhận hàng chi tiết (số nhà, đường/phố, phường...).";
    showFieldError("err-delivery-address", deliveryAddressInput, msg);
    errors.push(msg);
  }

  const timeErr = validateScheduledTime(true);
  if (timeErr) {
    errors.push(timeErr);
  }

  if (errors.length > 0) {
    showErrorBanner(errors);
    return false;
  }
  return true;
}

// ── 7. GỬI ĐƠN ĐẶT MÓN (TRONG TRANSACTION, CHỐNG BẤM 2 LẦN) ──────────────────
checkoutForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (isSubmittingOrder) return;

  if (!validateCheckoutForm()) {
    showCheckoutToast("Vui lòng kiểm tra lại các trường báo lỗi màu đỏ.", true);
    return;
  }

  isSubmittingOrder = true;
  btnPlaceOrder.disabled = true;
  btnPlaceOrder.innerHTML = `<i class="fa-solid fa-spinner fa-spin" aria-hidden="true"></i><span>Đang xử lý đơn hàng...</span>`;

  const mode = getSelectedDeliveryMode();
  const desiredDeliveryAt = mode === "SCHEDULED" ? desiredDeliveryInput.value : null;
  const idempotencyKey = `CHK-${Date.now()}-${Math.random().toString(36).slice(2, 7).toUpperCase()}`;

  const payload = {
    recipient_name: recipientNameInput.value.trim(),
    recipient_phone: recipientPhoneInput.value.trim().replace(/\s+/g, ""),
    delivery_address: deliveryAddressInput.value.trim(),
    delivery_area_id: Number(deliveryAreaSelect.value),
    payment_method: getSelectedPaymentMethod(),
    desired_delivery_at: desiredDeliveryAt,
    voucher_code: appliedVoucherCode,
    idempotency_key: idempotencyKey,
  };

  try {
    savePreferredPaymentMethod(payload.payment_method);
    const createdOrder = await api.post("/orders/checkout", payload);
    try {
      sessionStorage.setItem(LAST_ORDER_STORAGE_KEY, JSON.stringify(createdOrder));
    } catch (_) {}
    window.location.href = `order-result.html?order_id=${encodeURIComponent(createdOrder.id)}`;
  } catch (error) {
    const errMsg = error.message || "Không thể đặt đơn hàng. Vui lòng thử lại.";
    const isOutOfStock = /hết hàng|đã hết|ngừng bán|ngừng kinh doanh|bị ẩn/i.test(errMsg);
    if (isOutOfStock) {
      try {
        sessionStorage.setItem(LAST_ORDER_ERROR_KEY, errMsg);
      } catch (_) {}
      window.location.href = `order-result.html?status=out_of_stock&message=${encodeURIComponent(errMsg)}`;
      return;
    }
    showErrorBanner([errMsg]);
    showCheckoutToast(errMsg, true);
    isSubmittingOrder = false;
    await recalculateCartFromServer();
  }
});

function renderOrderSuccess(order) {
  checkoutForm.classList.add("hidden");
  errorBanner.classList.add("hidden");
  serverWarningBanner.classList.add("hidden");

  document.getElementById("success-order-code").textContent = order.order_code || `#${order.id}`;
  const area = getAreaById(order.delivery_area_id);
  const deliveryTimeText = order.desired_delivery_at
    ? `Hẹn giao lúc ${formatDateTime(order.desired_delivery_at)}`
    : "Giao ngay (30 – 45 phút)";
  const paymentText =
    order.payment_method === "COD"
      ? "Thanh toán khi nhận hàng (COD)"
      : "Chuyển khoản ngân hàng";

  document.getElementById("success-order-details").innerHTML = `
    <div class="space-y-2">
      <div class="flex justify-between gap-2">
        <span class="text-gray-500">Trạng thái:</span>
        <span class="rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-bold text-amber-800">Chờ xác nhận (${escapeHtml(order.status)})</span>
      </div>
      <div class="flex justify-between gap-2">
        <span class="text-gray-500">Người nhận:</span>
        <strong class="text-right">${escapeHtml(order.recipient_name)} · ${escapeHtml(order.recipient_phone)}</strong>
      </div>
      <div class="flex justify-between gap-2">
        <span class="text-gray-500">Địa chỉ:</span>
        <span class="text-right font-medium">${escapeHtml(order.delivery_address)}${area ? ` (${escapeHtml(area.name)})` : ""}</span>
      </div>
      <div class="flex justify-between gap-2">
        <span class="text-gray-500">Giờ giao:</span>
        <span class="font-medium">${escapeHtml(deliveryTimeText)}</span>
      </div>
      <div class="flex justify-between gap-2">
        <span class="text-gray-500">Thanh toán:</span>
        <span class="font-medium">${escapeHtml(paymentText)}</span>
      </div>
      <div class="border-t border-gray-200 pt-2 flex justify-between gap-2 text-base">
        <strong class="text-gray-900">Tổng thanh toán:</strong>
        <strong class="text-orange-600">${formatMoney(order.total_amount)}</strong>
      </div>
    </div>`;

  orderSuccessModal.classList.remove("hidden");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

// ── 8. KHỞI TẠO TRANG ────────────────────────────────────────────────────────
async function initCheckoutPage() {
  try {
    deliveryAreas = await api.get("/delivery-areas");
  } catch (_) {
    deliveryAreas = [
      { id: 1, name: "Quận Hà Đông", shipping_fee: 15000, is_active: true },
      { id: 2, name: "Quận Thanh Xuân", shipping_fee: 20000, is_active: true },
    ];
  }

  deliveryAreaSelect.innerHTML = [
    `<option value="">-- Chọn khu vực giao hàng --</option>`,
    ...deliveryAreas
      .filter((a) => a.is_active !== false)
      .map(
        (a) =>
          `<option value="${Number(a.id)}">${escapeHtml(a.name)} (Phí ship: ${formatMoney(a.shipping_fee)})</option>`,
      ),
  ].join("");

  restorePreferredPaymentMethod();
  loadAddressBook(deliveryAreas);
  if (addressBook.length > 0) {
    await selectAddressFromBook(addressBook[0].id, false);
  } else {
    renderAddressBook();
  }

  await recalculateCartFromServer();
}

initCheckoutPage();

