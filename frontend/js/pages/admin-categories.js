
const categoryTableBody = document.getElementById("category-table-body");
const categoryModal = document.getElementById("category-modal");
const categoryForm = document.getElementById("category-form");

let categories = [];

// ================================
// THÔNG BÁO
// ================================

function showMessage(message, type = "success") {
    const messageElement = document.getElementById("message");

    messageElement.textContent = message;
    messageElement.className = "mb-4 p-3 rounded-lg";

    if (type === "error") {
        messageElement.classList.add("bg-red-100", "text-red-700");
    } else {
        messageElement.classList.add("bg-green-100", "text-green-700");
    }

    setTimeout(function () {
        messageElement.classList.add("hidden");
    }, 3000);
}

// ================================
// CHỐNG CHÈN HTML KHÔNG AN TOÀN
// ================================

function escapeHTML(value) {
    return String(value || "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

// ================================
// TẢI DANH SÁCH DANH MỤC
// ================================

async function loadCategories() {
    try {
        categoryTableBody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center py-8 text-gray-500">
                    Đang tải danh mục...
                </td>
            </tr>
        `;

        const response = await api.get("/categories");

        if (Array.isArray(response)) {
            categories = response;
        } else {
            categories = response.items || response.data || [];
        }

        // Sắp xếp theo sort_order
        categories.sort(function (a, b) {
            const orderA = Number(a.sort_order || 0);
            const orderB = Number(b.sort_order || 0);

            if (orderA !== orderB) {
                return orderA - orderB;
            }

            return Number(a.id) - Number(b.id);
        });

        renderCategories();

    } catch (error) {
        console.error("Lỗi tải danh mục:", error);

        categoryTableBody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center py-8 text-red-500">
                    Không tải được danh sách danh mục.
                </td>
            </tr>
        `;

        showMessage(error.message, "error");
    }
}

// ================================
// HIỂN THỊ DANH SÁCH
// ================================

function renderCategories() {
    categoryTableBody.innerHTML = "";

    if (categories.length === 0) {
        categoryTableBody.innerHTML = `
            <tr>
                <td colspan="6" class="text-center py-8 text-gray-500">
                    Chưa có danh mục nào.
                </td>
            </tr>
        `;
        return;
    }

    for (let i = 0; i < categories.length; i++) {
        const category = categories[i];

        const row = document.createElement("tr");

        const statusHTML = category.is_active
            ? '<span class="category-status category-active">Đang hiển thị</span>'
            : '<span class="category-status category-hidden">Đã ẩn</span>';

        row.innerHTML = `
            <td class="px-4 py-3 font-medium">
                ${i + 1}
            </td>

            <td class="px-4 py-3 font-medium text-gray-800">
                ${escapeHTML(category.name)}
            </td>

            <td class="px-4 py-3 text-gray-600">
                ${escapeHTML(category.description || "Chưa có mô tả")}
            </td>

            <td class="px-4 py-3">
                ${statusHTML}
            </td>

            <td class="px-4 py-3">
                <div class="flex justify-center gap-2">
                    <button
                        class="sort-button"
                        data-action="up"
                        data-id="${category.id}"
                        ${i === 0 ? "disabled" : ""}
                        title="Di chuyển lên"
                    >
                        <i class="fa-solid fa-chevron-up"></i>
                    </button>

                    <button
                        class="sort-button"
                        data-action="down"
                        data-id="${category.id}"
                        ${i === categories.length - 1 ? "disabled" : ""}
                        title="Di chuyển xuống"
                    >
                        <i class="fa-solid fa-chevron-down"></i>
                    </button>
                </div>
            </td>

            <td class="px-4 py-3">
                <div class="flex justify-center gap-3">
                    <button
                        class="text-blue-600 hover:text-blue-800"
                        data-action="edit"
                        data-id="${category.id}"
                        title="Sửa danh mục"
                    >
                        <i class="fa-solid fa-pen"></i>
                    </button>

                    <button
                        class="${category.is_active ? "text-orange-600" : "text-green-600"} hover:opacity-70"
                        data-action="toggle"
                        data-id="${category.id}"
                        title="${category.is_active ? "Ẩn danh mục" : "Hiện danh mục"}"
                    >
                        <i class="fa-solid ${category.is_active ? "fa-eye-slash" : "fa-eye"}"></i>
                    </button>
                </div>
            </td>
        `;

        categoryTableBody.appendChild(row);
    }
}

// ================================
// MỞ POPUP THÊM DANH MỤC
// ================================

function openAddModal() {
    categoryForm.reset();

    document.getElementById("category-id").value = "";
    document.getElementById("modal-title").textContent = "Thêm danh mục";

    categoryModal.classList.remove("hidden");
    categoryModal.classList.add("flex");
}

// ================================
// MỞ POPUP SỬA DANH MỤC
// ================================

async function openEditModal(categoryId) {
    try {
        const category = await api.get("/categories/" + categoryId);

        document.getElementById("category-id").value = category.id;
        document.getElementById("category-name").value = category.name || "";
        document.getElementById("category-description").value =
            category.description || "";

        document.getElementById("modal-title").textContent = "Sửa danh mục";

        categoryModal.classList.remove("hidden");
        categoryModal.classList.add("flex");

    } catch (error) {
        showMessage("Không tải được danh mục: " + error.message, "error");
    }
}

// ================================
// ĐÓNG POPUP
// ================================

function closeModal() {
    categoryModal.classList.add("hidden");
    categoryModal.classList.remove("flex");
}

// ================================
// THÊM / SỬA DANH MỤC
// ================================

async function saveCategory(event) {
    event.preventDefault();

    const categoryId = document.getElementById("category-id").value;

    const name = document.getElementById("category-name").value.trim();
    const description = document.getElementById("category-description").value.trim();

    if (name === "") {
        showMessage("Vui lòng nhập tên danh mục.", "error");
        return;
    }

    const body = {
        name: name,
        description: description
    };

    try {
        if (categoryId) {
            await api.put("/categories/" + categoryId, body);
            showMessage("Cập nhật danh mục thành công.");
        } else {
            // Lấy thứ tự tiếp theo
            let maxOrder = 0;

            for (let i = 0; i < categories.length; i++) {
                if (categories[i].sort_order > maxOrder) {
                    maxOrder = categories[i].sort_order;
                }
            }

            body.sort_order = maxOrder + 1;
            body.is_active = true;

            await api.post("/categories", body);
            showMessage("Thêm danh mục thành công.");
        }

        closeModal();
        await loadCategories();

    } catch (error) {
        showMessage("Không thể lưu danh mục: " + error.message, "error");
    }
}

// ================================
// ẨN / HIỆN DANH MỤC
// ================================

async function toggleCategory(categoryId) {
    const category = categories.find(function (item) {
        return Number(item.id) === Number(categoryId);
    });

    if (!category) {
        return;
    }

    const newStatus = !category.is_active;

    const message = newStatus
        ? "Bạn muốn hiển thị lại danh mục này?"
        : "Bạn muốn ẩn danh mục này?";

    if (!confirm(message)) {
        return;
    }

    try {
        await api.patch("/categories/" + categoryId + "/status", {
            is_active: newStatus
        });

        showMessage(newStatus
            ? "Đã hiển thị danh mục."
            : "Đã ẩn danh mục."
        );

        await loadCategories();

    } catch (error) {
        showMessage("Không thể thay đổi trạng thái: " + error.message, "error");
    }
}

// ================================
// ĐỔI THỨ TỰ DANH MỤC
// ================================

async function moveCategory(categoryId, direction) {
    const currentIndex = categories.findIndex(function (item) {
        return Number(item.id) === Number(categoryId);
    });

    if (currentIndex === -1) {
        return;
    }

    let targetIndex;

    if (direction === "up") {
        targetIndex = currentIndex - 1;
    } else {
        targetIndex = currentIndex + 1;
    }

    // Không cho di chuyển vượt quá danh sách
    if (targetIndex < 0 || targetIndex >= categories.length) {
        return;
    }

    const currentCategory = categories[currentIndex];
    const targetCategory = categories[targetIndex];

    try {
        // Đưa danh mục hiện tại sang vị trí của danh mục bên cạnh
        await api.patch(
            "/categories/" + currentCategory.id + "/sort",
            {
                sort_order: targetIndex
            }
        );

        // Đưa danh mục bên cạnh về vị trí cũ
        await api.patch(
            "/categories/" + targetCategory.id + "/sort",
            {
                sort_order: currentIndex
            }
        );

        await loadCategories();

        showMessage("Đã cập nhật thứ tự danh mục.");

    } catch (error) {
        console.error("Lỗi sắp xếp:", error);

        showMessage(
            "Không thể sắp xếp danh mục: " + error.message,
            "error"
        );

        await loadCategories();
    }
}

// ================================
// SỰ KIỆN
// ================================

document.getElementById("add-category-button")
    .addEventListener("click", openAddModal);

document.getElementById("close-modal-button")
    .addEventListener("click", closeModal);

document.getElementById("cancel-modal-button")
    .addEventListener("click", closeModal);

document.getElementById("reload-button")
    .addEventListener("click", loadCategories);

categoryForm.addEventListener("submit", saveCategory);

// Bấm nền tối để đóng popup
categoryModal.addEventListener("click", function (event) {
    if (event.target === categoryModal) {
        closeModal();
    }
});

// Nhấn ESC để đóng popup
document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
        closeModal();
    }
});

// Xử lý các nút trong bảng
categoryTableBody.addEventListener("click", function (event) {
    const button = event.target.closest("button[data-action]");

    if (!button || button.disabled) {
        return;
    }

    const action = button.dataset.action;
    const categoryId = button.dataset.id;

    if (action === "edit") {
        openEditModal(categoryId);
    }

    if (action === "toggle") {
        toggleCategory(categoryId);
    }

    if (action === "up" || action === "down") {
        moveCategory(categoryId, action);
    }
});

// ================================
// KHỞI CHẠY
// ================================

loadCategories();
