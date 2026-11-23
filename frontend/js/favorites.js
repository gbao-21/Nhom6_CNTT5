(() => {
  const STORAGE_KEY = "favoriteDishes";
  let toastTimer;

  function normalizeDish(dish) {
    if (!dish || typeof dish !== "object") return null;
    const id = Number(dish.id);
    if (!Number.isInteger(id) || id < 1) return null;
    return {
      id,
      name: String(dish.name || `Món #${id}`),
      price: Number(dish.price) || 0,
      image_url: typeof dish.image_url === "string" ? dish.image_url : "",
    };
  }

  function getAll() {
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
      if (!Array.isArray(saved)) return [];
      const uniqueDishes = new Map();
      saved.forEach((dish) => {
        const normalized = normalizeDish(dish);
        if (normalized && !uniqueDishes.has(normalized.id)) {
          uniqueDishes.set(normalized.id, normalized);
        }
      });
      return Array.from(uniqueDishes.values());
    } catch (error) {
      console.warn("Không thể đọc danh sách món yêu thích:", error);
      return [];
    }
  }

  function save(dishes) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(dishes));
      updateCounts(dishes.length);
    } catch (error) {
      throw new Error("Không thể lưu món yêu thích trên thiết bị này.");
    }
  }

  function isFavorite(id) {
    return getAll().some((dish) => dish.id === Number(id));
  }

  function toggle(dish) {
    const normalized = normalizeDish(dish);
    if (!normalized) throw new Error("Không xác định được món ăn cần lưu.");

    const dishes = getAll();
    const existingIndex = dishes.findIndex((entry) => entry.id === normalized.id);
    if (existingIndex >= 0) {
      dishes.splice(existingIndex, 1);
      save(dishes);
      return false;
    }

    save([normalized, ...dishes]);
    return true;
  }

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (character) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    })[character]);
  }

  function buttonMarkup(dish) {
    const normalized = normalizeDish(dish);
    if (!normalized) return "";
    const active = isFavorite(normalized.id);
    const label = active
      ? `Bỏ ${normalized.name} khỏi danh sách yêu thích`
      : `Thêm ${normalized.name} vào danh sách yêu thích`;

    return `
      <button type="button" class="favorite-toggle" data-favorite-toggle
        data-favorite-id="${normalized.id}"
        data-favorite-name="${escapeHtml(normalized.name)}"
        data-favorite-price="${normalized.price}"
        data-favorite-image="${escapeHtml(normalized.image_url)}"
        aria-label="${escapeHtml(label)}" aria-pressed="${active}" title="${escapeHtml(label)}">
        <i class="${active ? "fa-solid" : "fa-regular"} fa-heart" aria-hidden="true"></i>
      </button>
    `;
  }

  function updateCounts(count = getAll().length) {
    document.querySelectorAll("[data-favorite-count]").forEach((badge) => {
      badge.textContent = String(count);
      badge.classList.toggle("hidden", count === 0);
    });
  }

  function updateButtons(id, active) {
    document.querySelectorAll("[data-favorite-toggle]").forEach((button) => {
      if (Number(button.dataset.favoriteId) !== id) return;
      const name = button.dataset.favoriteName || `Món #${id}`;
      const label = active
        ? `Bỏ ${name} khỏi danh sách yêu thích`
        : `Thêm ${name} vào danh sách yêu thích`;
      button.setAttribute("aria-pressed", String(active));
      button.setAttribute("aria-label", label);
      button.title = label;
      const icon = button.querySelector("i");
      if (icon) {
        icon.classList.toggle("fa-solid", active);
        icon.classList.toggle("fa-regular", !active);
      }
    });
  }

  function announce(message, isError = false) {
    if (typeof window.showCartToast === "function") {
      window.showCartToast(message, isError);
      return;
    }
    if (typeof window.showToast === "function") {
      window.showToast(message, isError ? "error" : "success");
      return;
    }

    let toast = document.getElementById("favorite-toast");
    if (!toast) {
      toast = document.createElement("div");
      toast.id = "favorite-toast";
      toast.className = "favorite-toast";
      toast.setAttribute("role", "status");
      toast.setAttribute("aria-live", "polite");
      document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.classList.toggle("is-error", isError);
    toast.classList.add("is-visible");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove("is-visible"), 3000);
  }

  function dispatchChange(id, active) {
    document.dispatchEvent(new CustomEvent("favorites:changed", {
      detail: { id, isFavorite: active, favorites: getAll() },
    }));
  }

  document.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-favorite-toggle]");
    if (!button) return;

    const id = Number(button.dataset.favoriteId);
    try {
      const active = toggle({
        id,
        name: button.dataset.favoriteName,
        price: button.dataset.favoritePrice,
        image_url: button.dataset.favoriteImage,
      });
      updateButtons(id, active);
      announce(
        active ? "Đã thêm món vào danh sách yêu thích." : "Đã bỏ món khỏi danh sách yêu thích.",
      );
      dispatchChange(id, active);
    } catch (error) {
      announce(error.message, true);
    }
  });

  window.FavoriteDishes = Object.freeze({
    getAll,
    isFavorite,
    buttonMarkup,
    updateCounts,
    announce,
    storageKey: STORAGE_KEY,
  });

  updateCounts();
})();
