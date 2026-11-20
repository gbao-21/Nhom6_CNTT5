const cartItems = document.getElementById("cart-items");
const cartItemCount = document.getElementById("cart-item-count");
const cartSummary = document.getElementById("cart-summary");
const clearCartButton = document.getElementById("clear-cart-button");
const cartMessage = document.getElementById("cart-message");

let currentCart = null;
let cartMessageTimer = null;

function getCartImageUrl(imageUrl) {
  if (!imageUrl) return "../assets/images/logo.svg";
  if (imageUrl.startsWith("/uploads/")) {
    return `${CONFIG.API_BASE_URL.replace(/\/api\/?$/, "")}${imageUrl}`;
  }
  return imageUrl;
}

function showCartMessage(message, isError = false) {
  cartMessage.textContent = message;
  cartMessage.setAttribute("role", isError ? "alert" : "status");
  cartMessage.setAttribute("aria-live", isError ? "assertive" : "polite");
  cartMessage.classList.remove("hidden", "bg-green-600", "bg-red-600");
  cartMessage.classList.add(isError ? "bg-red-600" : "bg-green-600");
  clearTimeout(cartMessageTimer);
  cartMessageTimer = setTimeout(() => cartMessage.classList.add("hidden"), 3200);
}

async function loadCart() {
  cartItems.innerHTML = `
    <div class="rounded-2xl border border-gray-100 bg-white p-8 text-center text-sm text-gray-500 shadow-sm">
      Đang tải các món trong giỏ...
    </div>`;
  cartSummary.classList.add("hidden");
  clearCartButton.classList.add("hidden");

  try {
    currentCart = await api.get("/carts/me");
    const items = Array.isArray(currentCart.items) ? currentCart.items : [];
    cartItemCount.textContent = `${currentCart.total_quantity || 0} món trong giỏ hàng`;

    if (items.length === 0) {
      cartItems.innerHTML = `
        <div class="rounded-2xl border border-gray-100 bg-white px-6 py-14 text-center shadow-sm">
          <div class="mb-4 text-5xl text-orange-300" aria-hidden="true">
            <i class="fa-solid fa-basket-shopping"></i>
          </div>
          <h2 class="text-lg font-bold text-gray-900">Giỏ hàng đang trống</h2>
          <p class="mt-2 text-sm text-gray-500">Chọn món bạn yêu thích và thêm vào giỏ nhé.</p>
          <a href="menu.html" class="mt-5 inline-flex items-center gap-2 rounded-xl bg-orange-600 px-5 py-3 text-sm font-bold text-white transition hover:bg-orange-700">
            <i class="fa-solid fa-utensils" aria-hidden="true"></i>
            Xem thực đơn
          </a>
        </div>`;
      return;
    }

    renderCartItems(items);
    renderCartSummary(currentCart);
    cartSummary.classList.remove("hidden");
    clearCartButton.classList.remove("hidden");
  } catch (error) {
    cartItemCount.textContent = "Không tải được giỏ hàng";
    cartItems.innerHTML = `
      <div class="rounded-2xl border border-red-100 bg-white p-6 text-center shadow-sm">
        <p class="text-sm text-red-600">${escapeHtml(error.message)}</p>
        <button type="button" data-action="reload" class="mt-4 rounded-lg bg-orange-600 px-4 py-2 text-sm font-semibold text-white hover:bg-orange-700">
          Thử tải lại
        </button>
      </div>`;
  }
}

function renderCartItems(items) {
  cartItems.innerHTML = `
    <div class="space-y-4">
      ${items.map((item) => {
        const options = (item.selected_options || [])
          .map((option) => `
            <span class="inline-flex items-center rounded-full bg-orange-50 px-2.5 py-1 text-xs text-orange-800">
              ${escapeHtml(option.name || "Tùy chọn")}
              ${Number(option.price) > 0 ? ` · +${formatMoney(option.price)}` : ""}
            </span>
          `)
          .join("");
        const warnings = (item.warnings || []).length
          ? `<p class="mt-2 text-xs text-red-600">${item.warnings.map(escapeHtml).join("<br>")}</p>`
          : "";

        return `
          <article class="rounded-2xl border border-gray-100 bg-white p-4 shadow-sm sm:p-5">
            <div class="flex flex-col gap-4 sm:flex-row">
              <img
                src="${escapeHtml(getCartImageUrl(item.dish_image_url))}"
                alt="${escapeHtml(item.dish_name || "Món ăn")}"
                class="h-28 w-full rounded-xl bg-gray-100 object-cover sm:h-28 sm:w-32"
                onerror="this.onerror=null;this.src='../assets/images/logo.svg'">
              <div class="min-w-0 flex-1">
                <div class="flex items-start justify-between gap-3">
                  <div>
                    <h2 class="font-bold text-gray-900">${escapeHtml(item.dish_name || `Món #${item.dish_id}`)}</h2>
                    <p class="mt-1 text-sm text-gray-500">${formatMoney(item.unit_price)} / phần</p>
                  </div>
                  <button
                    type="button"
                    data-action="remove"
                    data-id="${Number(item.id)}"
                    aria-label="Xóa ${escapeHtml(item.dish_name || "món ăn")} khỏi giỏ"
                    class="rounded-lg p-2 text-gray-400 transition hover:bg-red-50 hover:text-red-600">
                    <i class="fa-regular fa-trash-can" aria-hidden="true"></i>
                  </button>
                </div>
                ${options ? `<div class="mt-3 flex flex-wrap gap-2">${options}</div>` : ""}
                ${item.note ? `<p class="mt-2 text-xs text-gray-500">Ghi chú: ${escapeHtml(item.note)}</p>` : ""}
                ${warnings}
                <div class="mt-4 flex flex-wrap items-center justify-between gap-3">
                  <div class="inline-flex items-center rounded-lg border border-gray-200">
                    <button
                      type="button"
                      data-action="decrease"
                      data-id="${Number(item.id)}"
                      aria-label="Giảm số lượng"
                      ${item.quantity <= 1 ? "disabled" : ""}
                      class="h-9 w-9 rounded-l-lg text-gray-600 transition hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40">−</button>
                    <span class="min-w-10 px-2 text-center text-sm font-semibold">${Number(item.quantity)}</span>
                    <button
                      type="button"
                      data-action="increase"
                      data-id="${Number(item.id)}"
                      aria-label="Tăng số lượng"
                      class="h-9 w-9 rounded-r-lg text-gray-600 transition hover:bg-gray-50">＋</button>
                  </div>
                  <strong class="text-base font-extrabold text-orange-600">${formatMoney(item.line_total)}</strong>
                </div>
              </div>
            </div>
          </article>`;
      }).join("")}
    </div>`;
}

function renderCartSummary(cart) {
  document.getElementById("cart-subtotal").textContent = formatMoney(cart.subtotal);
  document.getElementById("cart-shipping").textContent = cart.shipping_fee
    ? formatMoney(cart.shipping_fee)
    : "Tính khi chọn khu vực";
  document.getElementById("cart-discount").textContent = `− ${formatMoney(cart.discount_amount)}`;
  document.getElementById("cart-discount-row").classList.toggle(
    "hidden",
    !Number(cart.discount_amount),
  );
  document.getElementById("cart-total").textContent = formatMoney(cart.total_amount);
}

cartItems.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;

  if (button.dataset.action === "reload") {
    loadCart();
    return;
  }

  const cartItemId = Number(button.dataset.id);
  const item = (currentCart?.items || []).find((cartItem) => cartItem.id === cartItemId);
  if (!item) return;

  button.disabled = true;
  try {
    if (button.dataset.action === "remove") {
      await api.delete(`/carts/items/${cartItemId}`);
      showCartMessage(`Đã xóa "${item.dish_name || "món ăn"}" khỏi giỏ hàng.`);
    } else {
      const change = button.dataset.action === "increase" ? 1 : -1;
      await api.put(`/carts/items/${cartItemId}`, {
        quantity: item.quantity + change,
      });
      showCartMessage("Đã cập nhật số lượng món.");
    }
    await loadCart();
  } catch (error) {
    button.disabled = false;
    showCartMessage(error.message, true);
  }
});

clearCartButton.addEventListener("click", async () => {
  if (!currentCart || currentCart.items.length === 0) return;
  if (!window.confirm("Bạn có chắc muốn xóa tất cả món trong giỏ hàng?")) return;

  clearCartButton.disabled = true;
  try {
    await api.delete("/carts/clear");
    showCartMessage("Đã xóa toàn bộ giỏ hàng.");
    await loadCart();
  } catch (error) {
    showCartMessage(error.message, true);
  } finally {
    clearCartButton.disabled = false;
  }
});

loadCart();
