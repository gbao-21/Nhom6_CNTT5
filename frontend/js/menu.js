const API_BASE_URL = "http://127.0.0.1:8000/api";

function formatVND(amount) {
    return new Intl.NumberFormat("vi-VN", {
        style: "currency",
        currency: "VND",
    }).format(Number(amount || 0));
}

async function loadCustomerMenu() {
    const featuredEl = document.getElementById("featuredDishes");
    const navEl = document.getElementById("categoryTabs");
    const sectionsEl = document.getElementById("menuCategoriesContainer");

    try {
        const res = await fetch(`${API_BASE_URL}/menu/overview`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        const categories = data.categories || [];
        renderMenuContent(categories, featuredEl, navEl, sectionsEl);
    } catch (err) {
        console.error("Không tải được thực đơn:", err);
        sectionsEl.innerHTML = `
            <div class="text-center py-12 text-red-500 bg-white rounded-xl border">
                Không thể kết nối máy chủ thực đơn. Hãy kiểm tra Backend đã chạy tại cổng 8000 chưa.
            </div>
        `;
    }
}

function createDishCardHTML(dish) {
    const isSoldOut = !dish.is_available;
    const imgSrc =
        dish.image_url ||
        "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=600&q=80";

    return `
        <article class="dish-card ${isSoldOut ? "sold-out" : ""} bg-white rounded-2xl border border-gray-100 shadow-sm hover:shadow-md transition overflow-hidden flex flex-col justify-between relative">
            ${
                isSoldOut
                    ? `<span class="absolute top-3 left-3 z-10 bg-gray-800/90 text-white text-xs font-semibold px-2.5 py-1 rounded-full">Hết món</span>`
                    : ""
            }
            <div>
                <div class="aspect-[16/10] w-full overflow-hidden bg-gray-100">
                    <img src="${imgSrc}" alt="${dish.name}" class="w-full h-full object-cover hover:scale-105 transition duration-300">
                </div>
                <div class="p-4">
                    <h3 class="font-bold text-base text-gray-900 line-clamp-1">${dish.name}</h3>
                    <p class="text-xs text-gray-500 mt-1 line-clamp-2 min-h-[32px]">
                        ${dish.description || "Hương vị đậm đà, chế biến nóng hổi khi đặt."}
                    </p>
                </div>
            </div>
            <div class="px-4 pb-4 pt-1 flex items-center justify-between">
                <span class="font-extrabold text-orange-600 text-base">${formatVND(dish.price)}</span>
                <button
                    type="button"
                    onclick="handleQuickAdd(${dish.id}, '${dish.name.replace(/'/g, "\\'")}')"
                    ${isSoldOut ? "disabled" : ""}
                    title="${isSoldOut ? "Món đã hết" : "Thêm vào giỏ"}"
                    class="btn-add-dish w-9 h-9 rounded-full bg-orange-600 hover:bg-orange-700 text-white flex items-center justify-center shadow-sm transition">
                    <i class="fa-solid fa-plus text-sm"></i>
                </button>
            </div>
        </article>
    `;
}

function renderMenuContent(categories, featuredEl, navEl, sectionsEl) {
    navEl.innerHTML = "";
    sectionsEl.innerHTML = "";

    const allDishes = [];

    categories.forEach((cat, idx) => {
        const dishes = cat.dishes || [];
        allDishes.push(...dishes);

        // 1. Nút trên thanh danh mục dính trên cùng
        const tabBtn = document.createElement("button");
        tabBtn.type = "button";
        tabBtn.dataset.target = `section-cat-${cat.id}`;
        tabBtn.className = `cat-tab shrink-0 px-4 py-2 rounded-full text-sm font-semibold transition ${
            idx === 0
                ? "bg-orange-600 text-white shadow-sm"
                : "bg-gray-100 text-gray-700 hover:bg-orange-50 hover:text-orange-600"
        }`;
        tabBtn.textContent = cat.name;

        tabBtn.addEventListener("click", () => {
            setActiveCategoryTab(tabBtn);
            const targetSection = document.getElementById(`section-cat-${cat.id}`);
            if (targetSection) {
                targetSection.scrollIntoView({ behavior: "smooth", block: "start" });
            }
        });
        navEl.appendChild(tabBtn);

        // 2. Khu vực danh sách món theo từng danh mục
        const section = document.createElement("section");
        section.id = `section-cat-${cat.id}`;
        section.className = "scroll-mt-32";
        section.innerHTML = `
            <div class="flex items-baseline justify-between mb-4">
                <h2 class="text-xl md:text-2xl font-bold text-gray-900 border-l-4 border-orange-600 pl-3">
                    ${cat.name}
                </h2>
                <span class="text-xs text-gray-400">${dishes.length} món</span>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
                ${
                    dishes.length > 0
                        ? dishes.map(createDishCardHTML).join("")
                        : `<p class="text-sm text-gray-400 italic col-span-full">Chưa có món trong danh mục này.</p>`
                }
            </div>
        `;
        sectionsEl.appendChild(section);
    });

    // 3. Món nổi bật (lấy tối đa 4 món đang còn bán)
    const featuredList = allDishes.filter((d) => d.is_available).slice(0, 4);
    featuredEl.innerHTML =
        featuredList.length > 0
            ? featuredList.map(createDishCardHTML).join("")
            : `<p class="text-sm text-gray-400 col-span-full">Chưa có dữ liệu món nổi bật.</p>`;

    // Tự động đổi highlight danh mục khi người dùng cuộn trang
    setupScrollSpy();
}

function setActiveCategoryTab(activeBtn) {
    document.querySelectorAll(".cat-tab").forEach((btn) => {
        btn.classList.remove("bg-orange-600", "text-white", "shadow-sm");
        btn.classList.add("bg-gray-100", "text-gray-700");
    });
    activeBtn.classList.remove("bg-gray-100", "text-gray-700");
    activeBtn.classList.add("bg-orange-600", "text-white", "shadow-sm");
    activeBtn.scrollIntoView({ behavior: "smooth", inline: "center", block: "nearest" });
}

function setupScrollSpy() {
    const sections = document.querySelectorAll("section[id^='section-cat-']");
    window.addEventListener("scroll", () => {
        let currentId = "";
        sections.forEach((sec) => {
            const top = sec.offsetTop - 150;
            if (window.scrollY >= top) {
                currentId = sec.id;
            }
        });
        if (currentId) {
            const matchedTab = document.querySelector(`.cat-tab[data-target="${currentId}"]`);
            if (matchedTab) setActiveCategoryTab(matchedTab);
        }
    });
}

function handleQuickAdd(dishId, dishName) {
    const badge = document.getElementById("cartCountBadge");
    if (badge) {
        badge.textContent = Number(badge.textContent || 0) + 1;
    }
    showToast(`Đã thêm "${dishName}" vào giỏ hàng`);
}

function showToast(message) {
    const toast = document.getElementById("toastMessage");
    if (!toast) return;
    toast.textContent = message;
    toast.classList.remove("opacity-0", "translate-y-3", "pointer-events-none");
    setTimeout(() => {
        toast.classList.add("opacity-0", "translate-y-3", "pointer-events-none");
    }, 2200);
}

document.addEventListener("DOMContentLoaded", loadCustomerMenu);