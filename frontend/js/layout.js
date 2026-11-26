// Layout chung: tự chèn header (menu) và footer vào mọi trang,
// để không phải copy lại HTML menu ở từng file.
//
// Mỗi trang cần có:  <body data-root="./">   (trang ở thư mục gốc)
//              hoặc  <body data-root="../">  (trang trong thư mục pages/)
// và hai thẻ rỗng:   <header id="app-header"></header> ... <footer id="app-footer"></footer>

// Thêm trang mới vào menu: thêm 1 dòng vào mảng này (đường dẫn tính từ thư mục frontend/)
const MENU = [
  { href: "pages/menu.html", label: "Thực đơn" },
  { href: "pages/dish-detail.html", label: "Chi tiết món & Đánh giá" },
  { href: "pages/my-orders.html", label: "Đơn của tôi" },
];

function renderLayout() {
  const root = document.body.dataset.root || "./";
  const currentPath = window.location.pathname;
  const isHomePage = currentPath.endsWith("/index.html") || currentPath.endsWith("/");
  const isMyOrdersPage = currentPath.endsWith("/pages/my-orders.html");
  const isDishDetailPage = currentPath.endsWith("/pages/dish-detail.html");

  const visibleMenu = isHomePage || isMyOrdersPage || isDishDetailPage
    ? MENU.filter((item) => item.href !== "pages/my-orders.html")
    : MENU;

  const links = visibleMenu.map((item) => {
    const isActive = currentPath.endsWith("/" + item.href) ||
      (item.href === "index.html" && currentPath.endsWith("/"));
    return `<a href="${root}${item.href}" class="${isActive ? "active" : ""}">${item.label}</a>`;
  }).join("");

  document.getElementById("app-header").innerHTML = `
    <div class="container header-inner">
      <nav class="nav">${links}</nav>
    </div>`;

  document.getElementById("app-footer").innerHTML = `
    <div class="container">© ${new Date().getFullYear()} HN-KS25-CNTT1 · Base code thực tập doanh nghiệp</div>`;
}

renderLayout();
