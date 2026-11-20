
const dishTableBody = document.getElementById("dish-table-body");
const categoryFilter = document.getElementById("category-filter");
const dishCategory = document.getElementById("dish-category");
const searchInput = document.getElementById("search-input");
const statusFilter = document.getElementById("status-filter");

const formSection = document.getElementById("dish-form-section");
const dishForm = document.getElementById("dish-form");
const optionsContainer = document.getElementById("options-container");
const imagePreview = document.getElementById("image-preview");

let categories = [];
let dishes = [];
let currentOptions = [];

// ================================
// HIỂN THỊ THÔNG BÁO
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
// TẢI DANH MỤC
// ================================

async function loadCategories() {
    try {
        const response = await api.get("/categories");

        if (Array.isArray(response)) {
            categories = response;
        } else {
            categories = response.items || response.data || [];
        }

        categoryFilter.innerHTML = '<option value="">Tất cả danh mục</option>';
        dishCategory.innerHTML = '<option value="">Chọn danh mục</option>';

        for (let i = 0; i < categories.length; i++) {
            const category = categories[i];

            const filterOption = document.createElement("option");
            filterOption.value = category.id;
            filterOption.textContent = category.name;
            categoryFilter.appendChild(filterOption);

            const formOption = document.createElement("option");
            formOption.value = category.id;
            formOption.textContent = category.name;
            dishCategory.appendChild(formOption);
        }
    } catch (error) {
        showMessage("Không tải được danh mục: " + error.message, "error");
    }
}

// ================================
// TẢI DANH SÁCH MÓN ĂN
// ================================

async function loadDishes() {
    try {
        dishTableBody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center py-8 text-gray-500">
                    Đang tải dữ liệu...
                </td>
            </tr>
        `;

        const params = {};

        if (searchInput.value.trim() !== "") {
            params.q = searchInput.value.trim();
        }

        if (categoryFilter.value !== "") {
            params.category_id = categoryFilter.value;
        }

        if (statusFilter.value !== "") {
            params.status = statusFilter.value;
        }

        const response = await api.get("/dishes", params);

        if (Array.isArray(response)) {
            dishes = response;
        } else {
            dishes = response.items || response.data || [];
        }

        renderDishes();
    } catch (error) {
        dishTableBody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center py-8 text-red-500">
                    Không tải được danh sách món ăn.
                </td>
            </tr>
        `;

        showMessage("Lỗi tải món ăn: " + error.message, "error");
    }
}

// ================================
// LẤY TÊN DANH MỤC
// ================================

function getCategoryName(categoryId) {
    for (let i = 0; i < categories.length; i++) {
        if (Number(categories[i].id) === Number(categoryId)) {
            return categories[i].name;
        }
    }

    return "Chưa phân loại";
}

// ================================
// HIỂN THỊ TRẠNG THÁI
// ================================

function getStatusHTML(status) {
    if (status === "AVAILABLE") {
        return '<span class="status-label status-available">Đang bán</span>';
    }

    if (status === "OUT_OF_STOCK") {
        return '<span class="status-label status-out-of-stock">Hết món</span>';
    }

    return '<span class="status-label status-hidden">Đã ẩn</span>';
}

// ================================
// HIỂN THỊ DANH SÁCH MÓN
// ================================

function renderDishes() {
    dishTableBody.innerHTML = "";

    if (dishes.length === 0) {
        dishTableBody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center py-8 text-gray-500">
                    Không có món ăn nào.
                </td>
            </tr>
        `;
        return;
    }

    for (let i = 0; i < dishes.length; i++) {
        const dish = dishes[i];

        const row = document.createElement("tr");

        const imageUrl = dish.image_url || "";

        row.innerHTML = `
            <td class="px-4 py-3">
                <img
                    src="${escapeHTML(imageUrl)}"
                    class="dish-thumbnail"
                    alt="${escapeHTML(dish.name || "Món ăn")}"
                    onerror="this.style.display='none'"
                >
            </td>

            <td class="px-4 py-3 font-medium">
                ${escapeHTML(dish.name || "")}
            </td>

            <td class="px-4 py-3">
                ${escapeHTML(getCategoryName(dish.category_id))}
            </td>

            <td class="px-4 py-3">
                ${Number(dish.price || 0).toLocaleString("vi-VN")} đ
            </td>

            <td class="px-4 py-3">
                ${getStatusHTML(dish.status)}
            </td>

            <td class="px-4 py-3">
                ${dish.is_featured ? "Có" : "Không"}
            </td>

            <td class="px-4 py-3">
                <div class="flex justify-center gap-3">
                    <button
                        class="text-blue-600 hover:text-blue-800"
                        data-action="edit"
                        data-id="${dish.id}"
                        title="Sửa"
                    >
                        <i class="fa-solid fa-pen"></i>
                    </button>

                    <button
                        class="text-orange-600 hover:text-orange-800"
                        data-action="hide"
                        data-id="${dish.id}"
                        title="Ẩn món"
                    >
                        <i class="fa-solid fa-eye-slash"></i>
                    </button>
                </div>
            </td>
        `;

        dishTableBody.appendChild(row);
    }
}

// ================================
// CHỐNG CHÈN HTML KHÔNG AN TOÀN
// ================================

function escapeHTML(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

// ================================
// MỞ FORM THÊM MÓN
// ================================

function openAddForm() {
    dishForm.reset();
    document.getElementById("dish-image-file").value = "";
    document.getElementById("dish-id").value = "";
    document.getElementById("form-title").textContent = "Thêm món ăn";

    imagePreview.src = "";
    imagePreview.classList.add("hidden");

    currentOptions = [];
    renderOptions();

    formSection.classList.remove("hidden");
    formSection.scrollIntoView({ behavior: "smooth" });
}

// ================================
// MỞ FORM SỬA MÓN
// ================================

async function openEditForm(dishId) {
    try {
        const dish = await api.get("/dishes/" + dishId);

        document.getElementById("dish-id").value = dish.id;
        document.getElementById("dish-name").value = dish.name || "";
        document.getElementById("dish-category").value = dish.category_id || "";
        document.getElementById("dish-price").value = dish.price || "";
        document.getElementById("dish-status").value = dish.status || "AVAILABLE";
        document.getElementById("dish-description").value = dish.description || "";
        document.getElementById("dish-image-url").value = dish.image_url || "";
        document.getElementById("dish-featured").checked = Boolean(dish.is_featured);

        if (dish.image_url) {
            imagePreview.src = dish.image_url;
            imagePreview.classList.remove("hidden");
        } else {
            imagePreview.classList.add("hidden");
        }

        const optionResponse = await api.get("/dishes/" + dishId + "/options");

        if (Array.isArray(optionResponse)) {
            currentOptions = optionResponse;
        } else {
            currentOptions = optionResponse.items || optionResponse.data || [];
        }

        document.getElementById("form-title").textContent = "Cập nhật món ăn";

        renderOptions();
        formSection.classList.remove("hidden");
        formSection.scrollIntoView({ behavior: "smooth" });
    } catch (error) {
        showMessage("Không tải được thông tin món ăn: " + error.message, "error");
    }
}

// ================================
// HIỂN THỊ CÁC TÙY CHỌN
// ================================

function renderOptions() {
    optionsContainer.innerHTML = "";

    if (currentOptions.length === 0) {
        optionsContainer.innerHTML = `
            <p class="text-sm text-gray-400">
                Chưa có tùy chọn nào.
            </p>
        `;
        return;
    }

    for (let i = 0; i < currentOptions.length; i++) {
        const option = currentOptions[i];

        const optionRow = document.createElement("div");
        optionRow.className = "option-row";

        optionRow.innerHTML = `
            <div>
                <label>Nhóm tùy chọn</label>
                <select class="option-group">
                    <option value="Size" ${option.group_name === "Size" ? "selected" : ""}>Size</option>
                    <option value="Topping" ${option.group_name === "Topping" ? "selected" : ""}>Topping</option>
                </select>
            </div>

            <div>
                <label>Tên tùy chọn</label>
                <input
                    type="text"
                    class="option-name"
                    value="${escapeHTML(option.name || "")}"
                    placeholder="Ví dụ: Size L"
                >
            </div>

            <div>
                <label>Giá thêm (VNĐ)</label>
                <input
                    type="number"
                    class="option-price"
                    min="0"
                    value="${Number(option.price || 0)}"
                >
            </div>

            <div>
                <button
                    type="button"
                    class="remove-option text-red-500 hover:text-red-700 px-3 py-2"
                    title="Xóa tùy chọn"
                >
                    <i class="fa-solid fa-trash"></i>
                </button>
            </div>
        `;

        optionsContainer.appendChild(optionRow);

        optionRow.querySelector(".remove-option").addEventListener("click", function () {
            currentOptions.splice(i, 1);
            renderOptions();
        });
    }
}

// ================================
// THÊM DÒNG TÙY CHỌN
// ================================

function addOption() {
    currentOptions.push({
        group_name: "Size",
        name: "",
        price: 0,
        is_available: true,
        is_required: false,
        allow_multiple: false
    });

    renderOptions();
}

// ================================
// LẤY DỮ LIỆU TÙY CHỌN TỪ FORM
// ================================

function getOptionsFromForm() {
    const optionRows = optionsContainer.querySelectorAll(".option-row");
    const result = [];

    for (let i = 0; i < optionRows.length; i++) {
        const row = optionRows[i];

        const groupName = row.querySelector(".option-group").value;
        const name = row.querySelector(".option-name").value.trim();
        const price = Number(row.querySelector(".option-price").value);

        if (name === "") {
            throw new Error("Vui lòng nhập tên cho tất cả tùy chọn.");
        }

        if (price < 0 || !Number.isFinite(price)) {
            throw new Error("Giá thêm của tùy chọn không hợp lệ.");
        }

        const oldOption = currentOptions[i];

        result.push({
            id: oldOption ? oldOption.id : null,
            group_name: groupName,
            name: name,
            price: price,
            is_available: oldOption ? oldOption.is_available : true,
            is_required: oldOption ? oldOption.is_required : false,
            allow_multiple: oldOption ? oldOption.allow_multiple : false
        });
    }

    return result;
}

// ================================
// LƯU TÙY CHỌN SAU KHI LƯU MÓN
// ================================

async function saveOptions(dishId, options) {
    const oldOptions = currentOptions;

    // Xóa những tùy chọn cũ đã bị loại khỏi form.
    for (let i = 0; i < oldOptions.length; i++) {
        const oldOption = oldOptions[i];

        if (!oldOption.id) {
            continue;
        }

        let exists = false;

        for (let j = 0; j < options.length; j++) {
            if (Number(options[j].id) === Number(oldOption.id)) {
                exists = true;
                break;
            }
        }

        if (!exists) {
            await api.delete(
                "/dishes/" + dishId + "/options/" + oldOption.id
            );
        }
    }

    // Thêm mới hoặc cập nhật tùy chọn.
    for (let i = 0; i < options.length; i++) {
        const option = options[i];

        const body = {
            group_name: option.group_name,
            name: option.name,
            price: option.price,
            is_available: option.is_available,
            is_required: option.is_required,
            allow_multiple: option.allow_multiple
        };

        if (option.id) {
            await api.put(
                "/dishes/" + dishId + "/options/" + option.id,
                body
            );
        } else {
            await api.post("/dishes/" + dishId + "/options", body);
        }
    }
}

// ================================
// THÊM / CẬP NHẬT MÓN ĂN
// ================================

async function submitDishForm(event) {
    event.preventDefault();

    try {
        const dishId = document.getElementById("dish-id").value;
        const imageFile = document.getElementById("dish-image-file").files[0];

        const priceInput = document.getElementById("dish-price").value.trim();
        const price = Number(priceInput);

        if (priceInput === "" || !Number.isFinite(price) || price <= 0) {
            showMessage("Giá bán phải là số lớn hơn 0.", "error");
            return;
        }

        const body = {
            name: document.getElementById("dish-name").value.trim(),
            category_id: Number(document.getElementById("dish-category").value),
            price: price,
            description: document.getElementById("dish-description").value.trim(),
            image_url: document.getElementById("dish-image-url").value.trim(),
            status: document.getElementById("dish-status").value,
            is_featured: document.getElementById("dish-featured").checked
        };

        if (body.name === "") {
            showMessage("Vui lòng nhập tên món ăn.", "error");
            return;
        }

        if (!body.category_id) {
            showMessage("Vui lòng chọn danh mục.", "error");
            return;
        }

        if (body.price <= 0 || !Number.isFinite(body.price)) {
            showMessage("Giá món ăn phải lớn hơn 0.", "error");
            return;
        }

        const options = getOptionsFromForm();

        let savedDish;

        // Thêm hoặc cập nhật món ăn
        if (dishId) {
            savedDish = await api.put("/dishes/" + dishId, body);
        } else {
            savedDish = await api.post("/dishes", body);
        }

        const savedDishId = dishId || savedDish.id;

        // Upload ảnh nếu người dùng đã chọn file
        if (imageFile) {
            const formData = new FormData();
            formData.append("file", imageFile);

            const imageResponse = await api.upload(
                "/dishes/" + savedDishId + "/image",
                formData
            );

            // Cập nhật đường dẫn ảnh nhận được từ backend
            document.getElementById("dish-image-url").value =
                imageResponse.image_url || "";
        }

        // Lưu các tùy chọn Size và Topping
        await saveOptions(savedDishId, options);

        showMessage(
            dishId ? "Cập nhật món ăn thành công." : "Thêm món ăn thành công."
        );

        formSection.classList.add("hidden");

        // Xóa file đã chọn để lần sau không upload nhầm ảnh cũ
        document.getElementById("dish-image-file").value = "";

        await loadDishes();

    } catch (error) {
        showMessage("Không thể lưu món ăn: " + error.message, "error");
    }
}

// ================================
// ẨN MÓN ĂN
// ================================

async function hideDish(dishId) {
    const confirmHide = confirm("Bạn có chắc muốn ẩn món ăn này?");

    if (!confirmHide) {
        return;
    }

    try {
        await api.patch("/dishes/" + dishId + "/hide");

        showMessage("Đã ẩn món ăn.");
        await loadDishes();
    } catch (error) {
        showMessage("Không thể ẩn món ăn: " + error.message, "error");
    }
}

// ================================
// SỰ KIỆN
// ================================

document.getElementById("add-dish-button").addEventListener("click", openAddForm);

document.getElementById("close-form-button").addEventListener("click", function () {
    formSection.classList.add("hidden");
});

document.getElementById("cancel-form-button").addEventListener("click", function () {
    formSection.classList.add("hidden");
});

document.getElementById("add-option-button").addEventListener("click", addOption);

document.getElementById("reload-button").addEventListener("click", loadDishes);

searchInput.addEventListener("input", loadDishes);
categoryFilter.addEventListener("change", loadDishes);
statusFilter.addEventListener("change", loadDishes);

dishForm.addEventListener("submit", submitDishForm);

dishTableBody.addEventListener("click", function (event) {
    const button = event.target.closest("button[data-action]");

    if (!button) {
        return;
    }

    const dishId = button.dataset.id;
    const action = button.dataset.action;

    if (action === "edit") {
        openEditForm(dishId);
    }

    if (action === "hide") {
        hideDish(dishId);
    }
});

// Xem trước ảnh được chọn
document.getElementById("dish-image-file").addEventListener("change", function () {
    const file = this.files[0];

    if (!file) {
        return;
    }

    const imageUrl = URL.createObjectURL(file);

    imagePreview.src = imageUrl;
    imagePreview.classList.remove("hidden");
});

// ================================
// KHỞI CHẠY TRANG
// ================================

async function initPage() {
    await loadCategories();
    await loadDishes();
}

initPage();
