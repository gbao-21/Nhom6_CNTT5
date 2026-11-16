// Trang khách hàng: Xem và đánh giá đơn hàng đã hoàn thành
// GET  /api/reviews/order/{order_id}  -> danh sách reviews đã có của đơn
// POST /api/reviews                   -> gửi đánh giá mới
// Quy tắc: chỉ đơn COMPLETED mới cho đánh giá; mỗi dish chỉ 1 lần

const btnLoad = document.getElementById("btn-load-order");
const orderIdInput = document.getElementById("order-id-input");
const orderInfo = document.getElementById("order-info");
const orderStatusInfo = document.getElementById("order-status-info");
const reviewsSection = document.getElementById("reviews-section");
const dishReviewsList = document.getElementById("dish-reviews-list");

// Dùng user_id mặc định = 1 (chưa có auth)
const DEFAULT_USER_ID = 1;

// ---------- Helpers ----------
function starsHtml(rating) {
  const full = Math.round(rating);
  return "★".repeat(full) + "☆".repeat(5 - full);
}

function starInputHtml(dishId) {
  return [5, 4, 3, 2, 1].map((n) => `
    <input type="radio" name="rating_${dishId}" id="star_${dishId}_${n}" value="${n}" style="display:none;">
    <label for="star_${dishId}_${n}" style="cursor:pointer;font-size:1.5rem;color:#d1d5db;" 
           onmouseover="highlightStars('${dishId}',${n})" 
           onmouseout="resetStars('${dishId}')"
           onclick="selectStar('${dishId}',${n})">★</label>
  `).join("");
}

let selectedRatings = {}; // { dishId: rating }

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

// ---------- Load đơn hàng ----------
btnLoad.addEventListener("click", loadOrder);
orderIdInput.addEventListener("keydown", (e) => { if (e.key === "Enter") loadOrder(); });

async function loadOrder() {
  const orderId = orderIdInput.value.trim();
  if (!orderId) { showToast("Nhập ID đơn hàng", "error"); return; }

  orderInfo.hidden = true;
  reviewsSection.hidden = true;
  selectedRatings = {};

  try {
    // Lấy danh sách đánh giá của đơn (backend trả về cả order_status và items)
    const data = await api.get(`/reviews/order/${orderId}`);
    // data: { order_id, order_status, reviews: [...] }
    // Mỗi review: { id, dish_id, dish_name, rating, content, image_url, created_at }

    renderOrderInfo(data, orderId);
    renderDishReviews(data, orderId);

    orderInfo.hidden = false;
    reviewsSection.hidden = false;
  } catch (error) {
    showToast(error.message, "error");
    orderInfo.hidden = false;
    orderStatusInfo.innerHTML = `<p class="text-error">${escapeHtml(error.message)}</p>`;
    reviewsSection.hidden = true;
  }
}

function renderOrderInfo(data, orderId) {
  const status = data.order_status || "UNKNOWN";
  const statusLabel = { PENDING: "Chờ xác nhận", PROCESSING: "Đang xử lý", COMPLETED: "Hoàn thành", CANCELLED: "Đã huỷ" }[status] || status;
  const statusColor = status === "COMPLETED" ? "var(--color-success)" : "var(--color-muted)";
  orderStatusInfo.innerHTML = `
    <strong>Đơn hàng #${orderId}</strong>
    <span style="margin-left:12px;color:${statusColor};font-weight:600;">${statusLabel}</span>
    ${status !== "COMPLETED" ? `<p class="muted" style="margin:4px 0 0;">Chỉ đơn hoàn thành mới có thể đánh giá.</p>` : ""}
  `;
}

function renderDishReviews(data, orderId) {
  const reviews = data.reviews || [];
  const isCompleted = data.order_status === "COMPLETED";

  if (reviews.length === 0 && !isCompleted) {
    dishReviewsList.innerHTML = `<p class="muted">Đơn hàng chưa có thông tin để hiển thị.</p>`;
    return;
  }

  if (reviews.length === 0 && isCompleted) {
    dishReviewsList.innerHTML = `<p class="muted">Đơn hàng chưa được đánh giá món nào. Hãy dùng form bên dưới.</p>` + renderNewReviewForm(orderId, null);
    return;
  }

  dishReviewsList.innerHTML = reviews.map((r) => {
    const hasReview = r.id !== null && r.id !== undefined;
    return `
    <div style="border:1px solid var(--color-border);border-radius:var(--radius);padding:16px;margin-bottom:12px;">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">
        <strong>${escapeHtml(r.dish_name || "Món " + r.dish_id)}</strong>
        ${hasReview
          ? `<span style="color:#f59e0b;">${starsHtml(r.rating)} ${r.rating}/5</span>`
          : (isCompleted ? `<span class="muted" style="font-size:13px;">Chưa đánh giá</span>` : "")}
      </div>
      ${hasReview ? `
        <p style="margin:6px 0;">${escapeHtml(r.content || "")}</p>
        ${r.image_url ? `<img src="${escapeHtml(r.image_url)}" alt="" style="max-height:100px;border-radius:4px;">` : ""}
        <div class="muted" style="font-size:12px;margin-top:4px;">${r.created_at ? formatDateTime(r.created_at) : ""}</div>
      ` : (isCompleted ? renderNewReviewForm(orderId, r.dish_id, r.dish_name) : "")}
    </div>`;
  }).join("");
}

function renderNewReviewForm(orderId, dishId, dishName) {
  const dishIdInput = dishId
    ? `<input type="hidden" id="dish_id_field_${dishId}" value="${dishId}">`
    : `<div>
        <label>ID món ăn *</label>
        <input type="number" id="dish_id_field_new" min="1" placeholder="Nhập ID món" style="width:120px;">
       </div>`;
  const title = dishId ? (dishName || `Món ${dishId}`) : "Món mới";

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

// ---------- Submit đánh giá ----------
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
  if (!dishId) { showToast("Nhập ID món ăn", "error"); return; }

  const dishKey = form.dataset.dish || "new";
  const rating = selectedRatings[dishKey];
  if (!rating) { showToast("Chọn số sao", "error"); return; }

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
    loadOrder(); // reload lại trang
  } catch (error) {
    showToast(error.message, "error");
    submitBtn.disabled = false;
  }
});

