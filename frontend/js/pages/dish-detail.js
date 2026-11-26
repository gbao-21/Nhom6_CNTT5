const dishSelect = document.getElementById("dish-select");
const dishInfoCard = document.getElementById("dish-info-card");
const dishImage = document.getElementById("dish-image");
const dishName = document.getElementById("dish-name");
const dishPrice = document.getElementById("dish-price");
const dishDescription = document.getElementById("dish-description");
const dishStatusBadge = document.getElementById("dish-status-badge");
const dishOptions = document.getElementById("dish-options");
const dishOptionsEmpty = document.getElementById("dish-options-empty");
const dishQuantity = document.getElementById("dish-quantity");
const dishNote = document.getElementById("dish-note");
const dishTotalPrice = document.getElementById("dish-total-price");
const dishOrderForm = document.getElementById("dish-order-form");
const addToCartButton = document.getElementById("add-to-cart-button");
const dishFormError = document.getElementById("dish-form-error");
const dishPageStatus = document.getElementById("dish-page-status");

const dishReviewsCard = document.getElementById("dish-reviews-card");
const summaryAvgStars = document.getElementById("summary-avg-stars");
const summaryTotalText = document.getElementById("summary-total-text");
const summaryAvgNumber = document.getElementById("summary-avg-number");
const dishReviewsList = document.getElementById("dish-reviews-list");
const reviewEligibility = document.getElementById("dish-review-eligibility");
const reviewFormToggle = document.getElementById("review-form-toggle");
const dishReviewForm = document.getElementById("dish-review-form");
const dishReviewError = document.getElementById("dish-review-error");
const dishReviewSubmit = document.getElementById("dish-review-submit");

let currentDish = null;
let quantity = 1;
let detailRequestId = 0;
let unavailableRequiredGroup = false;

const RECENT_DISHES_KEY = "recentDishes";
const MAX_RECENT_DISHES = 6;

function saveRecentlyViewedDish(dish) {
  try {
    const stored = JSON.parse(localStorage.getItem(RECENT_DISHES_KEY) || "[]");
    const recent = Array.isArray(stored) ? stored : [];
    const item = {
      id: Number(dish.id),
      name: dish.name,
      price: Number(dish.price) || 0,
      image_url: dish.image_url || "",
    };
    const updated = [
      item,
      ...recent.filter((entry) => entry && Number(entry.id) !== item.id),
    ]
      .slice(0, MAX_RECENT_DISHES);
    localStorage.setItem(RECENT_DISHES_KEY, JSON.stringify(updated));
  } catch (error) {
    console.warn("Không thể lưu lịch sử món đã xem:", error);
  }
}

function starsHtml(rating) {
  const rounded = Math.max(0, Math.min(5, Math.round(Number(rating) || 0)));
  return "★".repeat(rounded) + "☆".repeat(5 - rounded);
}

function getDishIdFromUrl() {
  const id = Number(new URLSearchParams(window.location.search).get("id"));
  return Number.isInteger(id) && id > 0 ? id : null;
}

function resolveDishImage(imageUrl) {
  if (!imageUrl) return "../assets/images/logo.svg";
  if (imageUrl.startsWith("/uploads/")) {
    return `${CONFIG.API_BASE_URL.replace(/\/api\/?$/, "")}${imageUrl}`;
  }
  return imageUrl;
}

async function initDishes() {
  try {
    const dishes = await api.get("/dishes");
    if (!Array.isArray(dishes) || dishes.length === 0) {
      dishSelect.innerHTML = `<option value="">Chưa có món ăn nào</option>`;
      dishSelect.disabled = true;
      dishPageStatus.textContent = "Hiện chưa có món ăn trong thực đơn.";
      dishPageStatus.hidden = false;
      return;
    }

    dishSelect.innerHTML = dishes
      .map((dish) => `<option value="${Number(dish.id)}">${escapeHtml(dish.name)}</option>`)
      .join("");

    const requestedId = getDishIdFromUrl();
    const initialDish = dishes.find((dish) => dish.id === requestedId) || dishes[0];
    dishSelect.value = String(initialDish.id);
    await loadDishDetail(initialDish.id);
  } catch (error) {
    dishSelect.innerHTML = `<option value="">Không tải được danh sách món</option>`;
    dishSelect.disabled = true;
    dishPageStatus.textContent = error.message;
    dishPageStatus.hidden = false;
    showToast(error.message, "error");
  }
}

dishSelect.addEventListener("change", () => {
  const selectedId = Number(dishSelect.value);
  if (!selectedId) return;

  const newUrl = new URL(window.location);
  newUrl.searchParams.set("id", selectedId);
  window.history.replaceState({}, "", newUrl);
  loadDishDetail(selectedId);
});

async function loadDishDetail(dishId) {
  const requestId = ++detailRequestId;
  dishInfoCard.hidden = true;
  dishReviewsCard.hidden = true;
  dishPageStatus.hidden = true;
  dishFormError.hidden = true;
  reviewFormToggle.hidden = true;
  dishReviewForm.hidden = true;
  reviewEligibility.textContent = "";
  dishReviewForm.reset();
  updateReviewStars();
  dishReviewError.hidden = true;
  dishReviewsList.innerHTML = `<p class="muted">Đang tải đánh giá...</p>`;

  try {
    const [dish, reviewData] = await Promise.all([
      api.get(`/dishes/${dishId}`),
      api.get(`/reviews/dish/${dishId}`).catch(() => null),
    ]);
    if (requestId !== detailRequestId) return;

    currentDish = dish;
    saveRecentlyViewedDish(dish);
    quantity = 1;
    dishQuantity.textContent = quantity;
    dishNote.value = "";

    dishName.textContent = dish.name;
    dishPrice.textContent = formatMoney(dish.price);
    dishDescription.textContent = dish.description || "Món ngon được chế biến tươi mới tại quán.";
    dishImage.src = resolveDishImage(dish.image_url);
    dishImage.alt = dish.name;
    dishImage.onerror = () => {
      dishImage.onerror = null;
      dishImage.src = "../assets/images/logo.svg";
    };

    const isAvailable = Boolean(dish.is_available && dish.is_active);
    dishStatusBadge.textContent = isAvailable ? "Đang phục vụ" : "Tạm hết món";
    dishStatusBadge.classList.toggle("sold-out", !isAvailable);
    addToCartButton.disabled = !isAvailable;
    addToCartButton.querySelector("span").textContent = isAvailable
      ? "Thêm vào giỏ hàng"
      : "Món tạm hết";

    renderDishOptions(dish.options || []);
    updateDishTotal();
    dishInfoCard.hidden = false;

    if (reviewData) {
      const average = Number(reviewData.average_rating || 0);
      summaryAvgNumber.textContent = average.toFixed(1);
      summaryAvgStars.textContent = starsHtml(average);
      summaryTotalText.textContent = `${reviewData.total_reviews || 0} lượt đánh giá`;
      renderReviews(reviewData.reviews || []);
      dishReviewsCard.hidden = false;
      reviewEligibility.textContent = "Bạn có thể đánh giá món ăn ngay tại đây.";
      reviewFormToggle.hidden = false;
    }
  } catch (error) {
    if (requestId !== detailRequestId) return;
    dishPageStatus.textContent = error.message;
    dishPageStatus.hidden = false;
    showToast(error.message, "error");
  }
}

function renderDishOptions(options) {
  const availableOptions = options.filter((option) => option.is_available);
  const groups = new Map();
  options.forEach((option) => {
    if (!groups.has(option.group_name)) groups.set(option.group_name, []);
    groups.get(option.group_name).push(option);
  });

  unavailableRequiredGroup = false;
  dishOptionsEmpty.textContent = options.length > 0
    ? "Các tùy chọn hiện đang hết hàng."
    : "Món này chưa có tùy chọn thêm.";
  dishOptions.innerHTML = Array.from(groups.entries())
    .map(([groupName, groupOptions], index) => {
      const firstOption = groupOptions[0];
      const isRequired = Boolean(firstOption.is_required);
      const allowMultiple = Boolean(firstOption.allow_multiple);
      const availableInGroup = groupOptions.filter((option) => option.is_available);
      const inputType = allowMultiple ? "checkbox" : "radio";

      if (isRequired && availableInGroup.length === 0) {
        unavailableRequiredGroup = true;
      }

      const choices = groupOptions
        .map((option) => {
          const checked = isRequired && !allowMultiple && option.id === availableInGroup[0]?.id;
          const priceLabel = Number(option.price) > 0
            ? `+ ${formatMoney(option.price)}`
            : "Miễn phí";
          return `
            <label class="option-choice">
              <input
                type="${inputType}"
                name="option-group-${index}"
                value="${Number(option.id)}"
                data-option-id="${Number(option.id)}"
                ${checked ? "checked" : ""}
                ${option.is_available ? "" : "disabled"}>
              <span class="option-choice-name">${escapeHtml(option.name)}${option.is_available ? "" : " (hết)"}</span>
              <span class="option-choice-price">${priceLabel}</span>
            </label>
          `;
        })
        .join("");

      return `
        <fieldset class="option-group" ${isRequired ? "data-required-group" : ""} data-group-name="${escapeHtml(groupName)}">
          <div class="option-group-heading">
            <strong>${escapeHtml(groupName)}</strong>
            <span>${isRequired
              ? allowMultiple ? "Bắt buộc chọn ít nhất 1" : "Bắt buộc chọn 1"
              : allowMultiple ? "Có thể chọn nhiều" : "Tùy chọn"}</span>
          </div>
          ${choices}
          ${isRequired && availableInGroup.length === 0
            ? `<p class="dish-form-error">Nhóm tùy chọn này hiện chưa có lựa chọn khả dụng.</p>`
            : ""}
        </fieldset>
      `;
    })
    .join("");

  dishOptionsEmpty.hidden = availableOptions.length > 0;
  addToCartButton.disabled = addToCartButton.disabled || unavailableRequiredGroup;
}

function getSelectedOptions() {
  return Array.from(dishOptions.querySelectorAll("input:checked"))
    .map((input) => {
      const option = (currentDish.options || []).find(
        (item) => item.id === Number(input.dataset.optionId),
      );
      return option
        ? { option_id: option.id, name: option.name, price: Number(option.price) || 0 }
        : null;
    })
    .filter(Boolean);
}

function updateDishTotal() {
  if (!currentDish) return;
  const selectedPrice = getSelectedOptions()
    .reduce((total, option) => total + option.price, 0);
  const unitPrice = Number(currentDish.price) + selectedPrice;
  dishTotalPrice.textContent = formatMoney(unitPrice * quantity);
}

dishOptions.addEventListener("change", () => {
  updateDishTotal();
  dishFormError.hidden = true;
});

document.getElementById("quantity-decrease").addEventListener("click", () => {
  quantity = Math.max(1, quantity - 1);
  dishQuantity.textContent = quantity;
  updateDishTotal();
});

document.getElementById("quantity-increase").addEventListener("click", () => {
  quantity += 1;
  dishQuantity.textContent = quantity;
  updateDishTotal();
});

dishOrderForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!currentDish) return;

  const missingRequiredGroup = Array.from(
    dishOptions.querySelectorAll("[data-required-group]"),
  ).some((group) => !group.querySelector("input:checked"));

  if (missingRequiredGroup || unavailableRequiredGroup) {
    dishFormError.textContent = "Vui lòng chọn đầy đủ các tùy chọn bắt buộc.";
    dishFormError.hidden = false;
    return;
  }

  addToCartButton.disabled = true;
  dishFormError.hidden = true;
  try {
    await api.post("/carts/items", {
      dish_id: currentDish.id,
      selected_options: getSelectedOptions(),
      note: dishNote.value.trim() || null,
      quantity,
    });
    showToast(`Đã thêm ${quantity} phần "${currentDish.name}" vào giỏ hàng.`);
  } catch (error) {
    dishFormError.textContent = error.message;
    dishFormError.hidden = false;
    showToast(error.message, "error");
  } finally {
    addToCartButton.disabled =
      !(currentDish.is_available && currentDish.is_active) || unavailableRequiredGroup;
  }
});

function renderReviews(reviews) {
  if (!reviews.length) {
    dishReviewsList.innerHTML = `
      <div class="review-empty muted">
        <div aria-hidden="true">💬</div>
        <p>Chưa có đánh giá nào cho món ăn này.</p>
        <small>Hãy đặt món và để lại đánh giá đầu tiên nhé!</small>
      </div>`;
    return;
  }

  dishReviewsList.innerHTML = reviews
    .map((review) => `
      <article class="review-item">
        <div class="review-item-heading">
          <div>
            <strong>${escapeHtml(review.user_name || "Khách hàng")}</strong>
            <span class="review-stars">${starsHtml(review.rating)}</span>
            <span class="review-rating">${Number(review.rating) || 0}/5</span>
          </div>
          <time class="muted">${review.created_at ? escapeHtml(formatDateTime(review.created_at)) : ""}</time>
        </div>
        ${review.content
          ? `<p>${escapeHtml(review.content)}</p>`
          : `<p class="muted"><em>Khách hàng không để lại nhận xét bằng lời.</em></p>`}
        ${review.image_url
          ? `<img class="review-image" src="${escapeHtml(resolveUploadUrl(review.image_url))}" alt="Ảnh thực tế từ khách hàng">`
          : ""}
        ${review.shop_reply
          ? `<div class="shop-reply">
              <strong>Phản hồi từ quán${review.replied_at
                ? ` · ${escapeHtml(formatDateTime(review.replied_at))}`
                : ""}</strong>
              <p>${escapeHtml(review.shop_reply)}</p>
            </div>`
          : ""}
      </article>
    `)
    .join("");
}

reviewFormToggle.addEventListener("click", () => {
  dishReviewForm.hidden = !dishReviewForm.hidden;
  if (!dishReviewForm.hidden) {
    dishReviewForm.querySelector("input[name='dish-rating']").focus();
  }
});

dishReviewForm.addEventListener("change", (event) => {
  if (event.target.name === "dish-rating") updateReviewStars();
  dishReviewError.hidden = true;
});

dishReviewForm.addEventListener("input", () => {
  dishReviewError.hidden = true;
});

function updateReviewStars() {
  const selectedInput = dishReviewForm.querySelector("input[name='dish-rating']:checked");
  const selectedRating = selectedInput ? Number(selectedInput.value) : 0;
  dishReviewForm.querySelectorAll(".rating-input label").forEach((label) => {
    label.classList.toggle("is-selected", Number(label.dataset.rating) <= selectedRating);
  });
}

dishReviewForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const selectedRating = dishReviewForm.querySelector("input[name='dish-rating']:checked");

  if (!selectedRating || !currentDish) {
    dishReviewError.textContent = "Chọn số sao trước khi gửi đánh giá.";
    dishReviewError.hidden = false;
    return;
  }

  const reviewedDishId = currentDish.id;
  const submitLabel = dishReviewSubmit.textContent;
  dishReviewSubmit.disabled = true;
  dishReviewSubmit.textContent = "Đang gửi...";
  dishSelect.disabled = true;
  dishReviewError.hidden = true;

  try {
    await api.post("/reviews", {
      dish_id: reviewedDishId,
      rating: Number(selectedRating.value),
      content: document.getElementById("dish-review-content").value.trim() || null,
    });
    showToast("Cảm ơn bạn đã gửi đánh giá!");
    await loadDishDetail(reviewedDishId);
  } catch (error) {
    dishReviewError.textContent = error.message;
    dishReviewError.hidden = false;
    showToast(error.message, "error");
  } finally {
    dishReviewSubmit.disabled = false;
    dishReviewSubmit.textContent = submitLabel;
    dishSelect.disabled = false;
  }
});

initDishes();
