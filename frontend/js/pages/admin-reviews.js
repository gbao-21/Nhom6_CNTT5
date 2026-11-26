// Trang Admin quản lý đánh giá
// GET   /api/reviews/dish/{dish_id}            -> danh sách đánh giá + avg_rating
// POST  /api/reviews/{id}/reply?role=STAFF     -> trả lời đánh giá
// PATCH /api/reviews/{id}/hide?role=ADMIN      -> ẩn/hiện đánh giá

const btnLoad = document.getElementById("btn-load-reviews");
const dishIdInput = document.getElementById("dish-id-input");
const reviewList = document.getElementById("review-list");
const reviewSummary = document.getElementById("review-summary");
const avgRatingEl = document.getElementById("avg-rating");
const totalReviewsEl = document.getElementById("total-reviews");

const replyModal = document.getElementById("reply-modal");
const replyText = document.getElementById("reply-text");
const btnSubmitReply = document.getElementById("btn-submit-reply");
const btnCancelReply = document.getElementById("btn-cancel-reply");

let replyingReviewId = null;

// ---------- Helpers ----------
function starsHtml(rating) {
  const full = Math.round(rating);
  return "★".repeat(full) + "☆".repeat(5 - full);
}

// ---------- Load đánh giá ----------
btnLoad.addEventListener("click", loadReviews);
dishIdInput.addEventListener("keydown", (e) => { if (e.key === "Enter") loadReviews(); });

async function loadReviews() {
  const dishId = dishIdInput.value.trim();
  if (!dishId) { showToast("Nhập ID món ăn", "error"); return; }

  reviewList.innerHTML = `<p class="muted">Đang tải...</p>`;
  reviewSummary.hidden = true;

  try {
    const data = await api.get(`/reviews/dish/${dishId}`);
    // data: { dish_id, dish_name, average_rating, total_reviews, reviews: [...] }
    avgRatingEl.textContent = `${starsHtml(data.average_rating)} ${data.average_rating}`;
    totalReviewsEl.textContent = `${data.total_reviews} đánh giá`;
    reviewSummary.hidden = false;
    renderReviews(data.reviews);
  } catch (error) {
    reviewList.innerHTML = `<p class="text-error">${escapeHtml(error.message)}</p>`;
  }
}

function renderReviews(reviews) {
  if (!reviews || reviews.length === 0) {
    reviewList.innerHTML = `<p class="muted">Chưa có đánh giá nào.</p>`;
    return;
  }
  reviewList.innerHTML = reviews.map((r) => `
    <div style="border:1px solid var(--color-border);border-radius:var(--radius);padding:16px;margin-bottom:12px;${r.is_hidden ? "opacity:.5;" : ""}">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;">
        <div>
          <span style="color:#f59e0b;font-size:1.1rem;">${starsHtml(r.rating)}</span>
          <strong style="margin-left:8px;">${escapeHtml(r.user_name || "Người dùng " + r.user_id)}</strong>
          <span class="muted" style="font-size:12px;margin-left:8px;">${r.created_at ? formatDateTime(r.created_at) : ""}</span>
          ${r.is_hidden ? `<span style="font-size:12px;color:var(--color-danger);margin-left:8px;">[Đã ẩn]</span>` : ""}
        </div>
        <div style="display:flex;gap:6px;">
          <button class="btn btn-small" data-action="reply" data-id="${r.id}">Trả lời</button>
          <button class="btn btn-small btn-danger" data-action="toggle-hide" data-id="${r.id}" data-hidden="${r.is_hidden}">
            ${r.is_hidden ? "Hiện lại" : "Ẩn"}
          </button>
        </div>
      </div>
      <p style="margin:8px 0 4px;">${escapeHtml(r.content || "")}</p>
      ${r.image_url ? `<img src="${escapeHtml(resolveUploadUrl(r.image_url))}" alt="ảnh đánh giá" style="max-height:120px;border-radius:4px;margin-top:4px;">` : ""}
      ${r.shop_reply ? `
        <div style="margin-top:10px;padding:10px;background:var(--color-bg);border-radius:var(--radius);border-left:3px solid var(--color-primary);">
          <strong>Phản hồi của cửa hàng:</strong>
          <p style="margin:4px 0 0;">${escapeHtml(r.shop_reply)}</p>
        </div>` : ""}
    </div>`).join("");
}

// ---------- Delegate click trong danh sách đánh giá ----------
reviewList.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;
  const id = Number(button.dataset.id);
  if (button.dataset.action === "reply") openReplyModal(id);
  if (button.dataset.action === "toggle-hide") {
    const isHidden = button.dataset.hidden === "true";
    toggleHide(id, !isHidden);
  }
});

// ---------- Modal trả lời ----------
function openReplyModal(reviewId) {
  replyingReviewId = reviewId;
  replyText.value = "";
  replyModal.style.display = "flex";
  replyText.focus();
}

btnCancelReply.addEventListener("click", () => {
  replyModal.style.display = "none";
  replyingReviewId = null;
});

btnSubmitReply.addEventListener("click", async () => {
  const reply = replyText.value.trim();
  if (!reply) { showToast("Nhập nội dung trả lời", "error"); return; }

  btnSubmitReply.disabled = true;
  try {
    await api.post(`/reviews/${replyingReviewId}/reply`, { reply }, { role: "STAFF" });
    showToast("Đã gửi trả lời");
    replyModal.style.display = "none";
    replyingReviewId = null;
    loadReviews();
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    btnSubmitReply.disabled = false;
  }
});

// ---------- Ẩn / Hiện đánh giá ----------
async function toggleHide(reviewId, hide) {
  const action = hide ? "Ẩn" : "Hiện lại";
  if (!confirm(`${action} đánh giá này?`)) return;
  try {
    await api.patch(`/reviews/${reviewId}/hide`, { is_hidden: hide }, { role: "ADMIN" });
    showToast(`Đã ${action.toLowerCase()} đánh giá`);
    loadReviews();
  } catch (error) {
    showToast(error.message, "error");
  }
}

