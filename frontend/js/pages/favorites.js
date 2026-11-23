const favoritesGrid = document.getElementById("favorites-grid");
const favoritesCount = document.getElementById("favorites-count");

function getFavoriteImageUrl(imageUrl) {
  if (!imageUrl) return "../assets/images/logo.svg";
  if (imageUrl.startsWith("/uploads/")) {
    return `${CONFIG.API_BASE_URL.replace(/\/api\/?$/, "")}${imageUrl}`;
  }

  try {
    const url = new URL(imageUrl, window.location.origin);
    return ["http:", "https:"].includes(url.protocol)
      ? url.href
      : "../assets/images/logo.svg";
  } catch {
    return "../assets/images/logo.svg";
  }
}

function renderFavorites(dishes = FavoriteDishes.getAll()) {
  FavoriteDishes.updateCounts(dishes.length);
  favoritesCount.textContent = `${dishes.length} món yêu thích`;

  if (dishes.length === 0) {
    favoritesGrid.innerHTML = `
      <div class="favorites-empty">
        <div class="favorites-empty-icon" aria-hidden="true">
          <i class="fa-regular fa-heart"></i>
        </div>
        <h2>Danh sách yêu thích đang trống</h2>
        <p>Chạm vào biểu tượng trái tim trên món ăn để lưu lại và tìm nhanh sau này.</p>
        <a href="menu.html">
          <i class="fa-solid fa-utensils" aria-hidden="true"></i>
          Khám phá thực đơn
        </a>
      </div>
    `;
    return;
  }

  favoritesGrid.innerHTML = dishes.map((dish) => `
    <article class="favorite-card">
      <div class="favorite-card-image">
        <img src="${escapeHtml(getFavoriteImageUrl(dish.image_url))}"
          alt="${escapeHtml(dish.name)}" loading="lazy"
          onerror="this.onerror=null;this.src='../assets/images/logo.svg'">
        ${FavoriteDishes.buttonMarkup(dish)}
      </div>
      <div class="favorite-card-content">
        <h2>${escapeHtml(dish.name)}</h2>
        <p class="favorite-card-price">${formatMoney(dish.price)}</p>
        <div class="favorite-card-actions">
          <a href="dish-detail.html?id=${encodeURIComponent(String(dish.id))}">
            <i class="fa-solid fa-eye" aria-hidden="true"></i>
            Chi tiết
          </a>
          <button type="button" data-favorite-add="${Number(dish.id)}"
            data-dish-name="${escapeHtml(dish.name)}">
            <i class="fa-solid fa-cart-plus" aria-hidden="true"></i>
            Thêm vào giỏ
          </button>
        </div>
      </div>
    </article>
  `).join("");
}

favoritesGrid.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-favorite-add]");
  if (!button) return;

  const originalContent = button.innerHTML;
  button.disabled = true;
  button.textContent = "Đang thêm...";
  try {
    await api.post("/carts/items", {
      dish_id: Number(button.dataset.favoriteAdd),
      selected_options: [],
      quantity: 1,
    });
    showToast(`Đã thêm "${button.dataset.dishName}" vào giỏ hàng.`);
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    button.innerHTML = originalContent;
    button.disabled = false;
  }
});

document.addEventListener("favorites:changed", (event) => {
  renderFavorites(event.detail.favorites);
});

renderFavorites();
