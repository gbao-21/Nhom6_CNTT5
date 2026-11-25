
const currentPage = window.location.pathname.split("/").pop();

const menuItems = [
    {
        name: "Dashboard",
        icon: "fa-chart-line",
        file: "admin-dashboard.html"
    },
    {
        name: "Quản lý món ăn",
        icon: "fa-utensils",
        file: "admin-items.html"
    },
    {
        name: "Quản lý danh mục",
        icon: "fa-list",
        file: "admin-categories.html"
    },
    {
        name: "Quản lý mã giảm giá",
        icon: "fa-ticket",
        file: "admin-coupons.html"
    },
    {
        name: "Quản lý đánh giá",
        icon: "fa-star",
        file: "admin-reviews.html"
    },
    {
        name: "Chat với khách hàng",
        icon: "fa-comments",
        file: "staff-chat.html"
    }
];

// Tìm tên trang hiện tại
let pageTitle = "Dashboard";

for (let i = 0; i < menuItems.length; i++) {
    if (currentPage === menuItems[i].file) {
        pageTitle = menuItems[i].name;
        break;
    }
}

// Tạo danh sách menu
let menuHTML = "";

for (let i = 0; i < menuItems.length; i++) {
    let item = menuItems[i];

    let activeClass = "";

    if (currentPage === item.file) {
        activeClass = "active";
    }

    menuHTML += `
        <a href="${item.file}"
           class="admin-menu-item ${activeClass}">
            <i class="fa-solid ${item.icon}"></i>
            <span>${item.name}</span>
        </a>
    `;
}

// Tạo giao diện Sidebar
const sidebarHTML = `
    <div class="admin-overlay" id="admin-overlay"></div>

    <aside class="admin-sidebar">

        <div class="admin-brand">
            <i class="fa-solid fa-utensils"></i>
            <span>FOOD NIGHT</span>
        </div>

        <div class="admin-menu-title">
            QUẢN LÝ HỆ THỐNG
        </div>

        <nav class="admin-menu">
            ${menuHTML}
        </nav>

        <div class="admin-sidebar-footer">
            <strong>Food Night Admin</strong>
            <small>Management System</small>
        </div>

    </aside>

    <header class="admin-topbar">

        <button id="admin-menu-toggle" type="button">
            <i class="fa-solid fa-bars"></i>
        </button>

        <h2>${pageTitle}</h2>

    </header>
`;

// Chèn Sidebar vào trang
document.body.insertAdjacentHTML("afterbegin", sidebarHTML);

// Xử lý đóng mở Sidebar
const toggleButton = document.getElementById("admin-menu-toggle");
const overlay = document.getElementById("admin-overlay");

toggleButton.addEventListener("click", function () {
    if (window.innerWidth <= 768) {
        document.body.classList.toggle("sidebar-open");
    } else {
        document.body.classList.toggle("sidebar-collapsed");
    }
});

// Đóng Sidebar khi bấm ra ngoài trên điện thoại
overlay.addEventListener("click", function () {
    document.body.classList.remove("sidebar-open");
});
