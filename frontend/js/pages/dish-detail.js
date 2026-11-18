// Chi tiết món ăn & danh sách đánh giá
// API: GET /api/dishes/{id}
// API: GET /api/reviews/dish/{id}

const dishSelect = document.getElementById("dish-select");
const dishInfoCard = document.getElementById("dish-info-card");
const dishImage = document.getElementById("dish-image");
const dishName = document.getElementById("dish-name");
const dishPrice = document.getElementById("dish-price");
const dishDescription = document.getElementById("dish-description");
const dishStatusBadge = document.getElementById("dish-status-badge");

const dishReviewsCard = document.getElementById("dish-reviews-card");
const summaryAvgStars = document.getElementById("summary-avg-stars");
const summaryTotalText = document.getElementById("summary-total-text");
const summaryAvgNumber = document.getElementById("summary-avg-number");
const dishReviewsList = document.getElementById("dish-reviews-list");

function starsHtml(rating) {
  const rounded = Math.round(rating);
  return "★".repeat(rounded) + "☆".repeat(5 - rounded);
}

// Lấy dishId từ URL params (ví dụ ?id=1) nếu có
function getDishIdFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const id = params.get("id");
  return id ? Number(id) : null;
}

// 1. Tải danh sách món vào select box
async function initDishes() {
  try {
    const dishes = await api.get("/dishes");
    if (!dishes || dishes.length === 0) {
      dishSelect.innerHTML = `<option value="">Chưa có món ăn nào trong hệ thống</option>`;
      return;
    }

    dishSelect.innerHTML = dishes
      .map((d) => `<option value="${d.id}">${escapeHtml(d.name)} (#${d.id})</option>`)
      .join("");

    const initialId = getDishIdFromUrl() || dishes[0].id;
    dishSelect.value = initialId;
    loadDishDetail(initialId);
  } catch (err) {
    showToast(err.message, "error");
  }
}

dishSelect.addEventListener("change", () => {
  const selectedId = Number(dishSelect.value);
  if (selectedId) {
    // Cập nhật URL mà không reload trang
    const newUrl = new URL(window.location);
    newUrl.searchParams.set("id", selectedId);
    window.history.replaceState({}, "", newUrl);

    loadDishDetail(selectedId);
  }
});

// 2. Tải thông tin món và đánh giá
async function loadDishDetail(dishId) {
  dishInfoCard.hidden = true;
  dishReviewsCard.hidden = true;
  dishReviewsList.innerHTML = `<p class="muted">Đang tải đánh giá...</p>`;

  try {
    // Gọi song song thông tin món và danh sách đánh giá
    const [dish, reviewData] = await Promise.all([
      api.get(`/dishes/${dishId}`).catch(() => null),
      api.get(`/reviews/dish/${dishId}`).catch(() => null),
    ]);

    if (dish) {
      dishName.textContent = dish.name;
      dishPrice.textContent = formatMoney(dish.price);
      dishDescription.textContent = dish.description || "Chưa có mô tả chi tiết cho món ăn này.";
      dishImage.src = dish.image_url || "../assets/images/logo.svg";
      dishStatusBadge.textContent = dish.is_available ? "Đang mở bán" : "Tạm hết hàng";
      dishStatusBadge.style.background = dish.is_available ? "#dcfce7" : "#fee2e2";
      dishStatusBadge.style.color = dish.is_available ? "#166534" : "#991b1b";
      dishInfoCard.hidden = false;
    }

    if (reviewData) {
      const avg = Number(reviewData.average_rating || 0).toFixed(1);
      const total = reviewData.total_reviews || 0;

      summaryAvgNumber.textContent = avg;
      summaryAvgStars.textContent = starsHtml(Number(avg));
      summaryTotalText.textContent = `${total} lượt đánh giá`;

      renderReviews(reviewData.reviews || []);
      dishReviewsCard.hidden = false;
    }
  } catch (err) {
    showToast(err.message, "error");
  }
}

// 3. Render danh sách đánh giá của món
function renderReviews(reviews) {
  if (!reviews || reviews.length === 0) {
    dishReviewsList.innerHTML = `
      <div style="text-align:center;padding:32px 16px;" class="muted">
        <div style="font-size:2rem;margin-bottom:8px;">💬</div>
        <p style="margin:0;">Chưa có đánh giá nào cho món ăn này.</p>
        <p style="font-size:13px;margin-top:4px;">Hãy đặt món và để lại đánh giá đầu tiên nhé!</p>
      </div>`;
    return;
  }

  dishReviewsList.innerHTML = reviews
    .map((r) => `
      <div style="border-bottom:1px solid var(--color-border);padding:16px 0;">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px;">
          <div>
            <strong style="font-size:15px;">${escapeHtml(r.user_name || "Khách hàng")}</strong>
            <span style="color:#f59e0b;margin-left:8px;font-size:14px;">${starsHtml(r.rating)}</span>
            <span style="font-weight:600;font-size:13px;margin-left:4px;color:#f59e0b;">${r.rating}/5</span>
          </div>
          <span class="muted" style="font-size:12px;">${r.created_at ? formatDateTime(r.created_at) : ""}</span>
        </div>
        ${r.content ? `<p style="margin:6px 0;line-height:1.6;">${escapeHtml(r.content)}</p>` : `<p class="muted" style="font-style:italic;margin:4px 0;">(Khách hàng không để lại nhận xét bằng lời)</p>`}
        ${
          r.image_url
            ? `<div style="margin-top:8px;"><img src="${escapeHtml(r.image_url)}" alt="Ảnh thực tế" style="max-height:140px;border-radius:6px;border:1px solid var(--color-border);cursor:pointer;" onclick="window.open('${escapeHtml(r.image_url)}')"></div>`
            : ""
        }
        ${
          r.shop_reply
            ? `
          <div style="margin-top:10px;padding:12px;background:var(--color-bg);border-radius:var(--radius);border-left:3px solid var(--color-primary);">
            <div style="font-size:13px;font-weight:700;color:var(--color-primary);margin-bottom:4px;">
              Phản hồi từ quán ${r.replied_at ? `· <span class="muted" style="font-weight:normal;font-size:12px;">${formatDateTime(r.replied_at)}</span>` : ""}
            </div>
            <p style="margin:0;font-size:14px;">${escapeHtml(r.shop_reply)}</p>
          </div>`
            : ""
        }
      </div>
    `)
    .join("");
}

initDishes();

