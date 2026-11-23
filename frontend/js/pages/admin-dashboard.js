// Trang thống kê Dashboard Admin: gọi GET /api/dashboard và vẽ biểu đồ bằng Chart.js

const filterForm = document.getElementById("filter-form");
const periodSelect = document.getElementById("period-select");
const startDateInput = document.getElementById("start-date");
const endDateInput = document.getElementById("end-date");
const btnResetFilter = document.getElementById("btn-reset-filter");

const kpiRevenue = document.getElementById("kpi-revenue");
const kpiRevenueSub = document.getElementById("kpi-revenue-sub");
const kpiOrders = document.getElementById("kpi-orders");
const kpiOrdersSub = document.getElementById("kpi-orders-sub");
const kpiRating = document.getElementById("kpi-rating");
const kpiRatingSub = document.getElementById("kpi-rating-sub");
const kpiCoupons = document.getElementById("kpi-coupons");
const kpiCouponsSub = document.getElementById("kpi-coupons-sub");
const revenueChartTitle = document.getElementById("revenue-chart-title");

const bestSellerTbody = document.getElementById("best-seller-tbody");
const couponUsageTbody = document.getElementById("coupon-usage-tbody");

let revenueChartInstance = null;
let statusChartInstance = null;
let bestSellerChartInstance = null;
let couponChartInstance = null;

function toIsoDateString(d) {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function applyQuickRange(rangeKey) {
  const today = new Date();
  if (rangeKey === "all") {
    startDateInput.value = "";
    endDateInput.value = "";
  } else if (rangeKey === "7d") {
    const start = new Date(today);
    start.setDate(today.getDate() - 6);
    startDateInput.value = toIsoDateString(start);
    endDateInput.value = toIsoDateString(today);
    periodSelect.value = "day";
  } else if (rangeKey === "30d") {
    const start = new Date(today);
    start.setDate(today.getDate() - 29);
    startDateInput.value = toIsoDateString(start);
    endDateInput.value = toIsoDateString(today);
    periodSelect.value = "day";
  } else if (rangeKey === "month") {
    const start = new Date(today.getFullYear(), today.getMonth(), 1);
    startDateInput.value = toIsoDateString(start);
    endDateInput.value = toIsoDateString(today);
  }
  loadDashboardData();
}

document.querySelectorAll("[data-range]").forEach((btn) => {
  btn.addEventListener("click", () => applyQuickRange(btn.dataset.range));
});

filterForm.addEventListener("submit", (e) => {
  e.preventDefault();
  loadDashboardData();
});

periodSelect.addEventListener("change", () => {
  loadDashboardData();
});

btnResetFilter.addEventListener("click", () => {
  periodSelect.value = "day";
  startDateInput.value = "";
  endDateInput.value = "";
  loadDashboardData();
});

async function loadDashboardData() {
  const params = {
    period: periodSelect.value || "day",
  };
  if (startDateInput.value) params.start_date = startDateInput.value;
  if (endDateInput.value) params.end_date = endDateInput.value;

  try {
    const data = await api.get("/dashboard", params);
    renderKPIs(data);
    renderRevenueChart(data);
    renderStatusChart(data);
    renderBestSellerChart(data);
    renderCouponChart(data);
    renderTables(data);
  } catch (err) {
    showToast(err.message || "Không tải được dữ liệu thống kê", "error");
  }
}

function renderKPIs(data) {
  kpiRevenue.textContent = formatMoney(data.total_revenue || 0);
  kpiRevenueSub.textContent =
    data.start_date || data.end_date
      ? `Khoảng: ${data.start_date || "..."} → ${data.end_date || "..."}`
      : "Tất cả thời gian (đơn không huỷ)";

  kpiOrders.textContent = data.total_orders || 0;
  kpiOrdersSub.textContent = `${data.completed_orders || 0} đơn hoàn thành`;

  const avg = Number(data.average_rating || 0).toFixed(1);
  kpiRating.textContent = `${avg} ★`;
  kpiRatingSub.textContent = `${data.total_reviews || 0} lượt đánh giá`;

  kpiCoupons.textContent = data.total_coupons_used || 0;
  kpiCouponsSub.textContent = `${(data.coupon_usages || []).length} mã trong hệ thống`;
}

function renderRevenueChart(data) {
  const isMonth = data.period === "month";
  revenueChartTitle.textContent = isMonth ? "Doanh thu theo tháng" : "Doanh thu theo ngày";

  const series = data.revenue_series || [];
  const labels = series.length > 0 ? series.map((p) => p.label) : ["Chưa có dữ liệu"];
  const revenues = series.length > 0 ? series.map((p) => p.revenue) : [0];

  if (revenueChartInstance) revenueChartInstance.destroy();

  const ctx = document.getElementById("revenueChart").getContext("2d");
  revenueChartInstance = new Chart(ctx, {
    type: isMonth ? "bar" : "line",
    data: {
      labels,
      datasets: [
        {
          label: "Doanh thu (VNĐ)",
          data: revenues,
          borderColor: "#2563eb",
          backgroundColor: isMonth ? "rgba(37, 99, 235, 0.75)" : "rgba(37, 99, 235, 0.15)",
          borderWidth: 2.5,
          fill: !isMonth,
          tension: 0.3,
          borderRadius: isMonth ? 6 : 0,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: true },
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            callback: (val) => Number(val).toLocaleString("vi-VN") + " ₫",
          },
        },
      },
    },
  });
}

function renderStatusChart(data) {
  const items = data.orders_by_status || [];
  const labels = items.map((i) => i.label);
  const counts = items.map((i) => i.count);

  const colors = [
    "#f59e0b", // PENDING
    "#3b82f6", // CONFIRMED
    "#8b5cf6", // PREPARING
    "#06b6d4", // DELIVERING
    "#16a34a", // COMPLETED
    "#dc2626", // CANCELLED
  ];

  if (statusChartInstance) statusChartInstance.destroy();

  const ctx = document.getElementById("statusChart").getContext("2d");
  statusChartInstance = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels,
      datasets: [
        {
          data: counts,
          backgroundColor: colors,
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "right" },
      },
    },
  });
}

function renderBestSellerChart(data) {
  const dishes = data.best_selling_dishes || [];
  const labels = dishes.length > 0 ? dishes.map((d) => d.dish_name) : ["Chưa có đơn hàng"];
  const quantities = dishes.length > 0 ? dishes.map((d) => d.total_quantity) : [0];

  if (bestSellerChartInstance) bestSellerChartInstance.destroy();

  const ctx = document.getElementById("bestSellerChart").getContext("2d");
  bestSellerChartInstance = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Số lượng đã bán",
          data: quantities,
          backgroundColor: "rgba(234, 88, 12, 0.8)",
          borderColor: "#ea580c",
          borderWidth: 1,
          borderRadius: 6,
        },
      ],
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
      },
      scales: {
        x: {
          beginAtZero: true,
          ticks: { precision: 0 },
        },
      },
    },
  });
}

function renderCouponChart(data) {
  const coupons = data.coupon_usages || [];
  const labels = coupons.length > 0 ? coupons.map((c) => c.code) : ["Chưa có mã"];
  const usedCounts = coupons.length > 0 ? coupons.map((c) => c.used_count) : [0];

  if (couponChartInstance) couponChartInstance.destroy();

  const ctx = document.getElementById("couponChart").getContext("2d");
  couponChartInstance = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: "Số lượt đã dùng",
          data: usedCounts,
          backgroundColor: "rgba(22, 163, 74, 0.78)",
          borderColor: "#16a34a",
          borderWidth: 1,
          borderRadius: 6,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: { precision: 0 },
        },
      },
    },
  });
}

function renderTables(data) {
  const dishes = data.best_selling_dishes || [];
  if (dishes.length === 0) {
    bestSellerTbody.innerHTML = `<tr><td colspan="4" class="muted">Chưa có dữ liệu món bán chạy trong khoảng thời gian này.</td></tr>`;
  } else {
    bestSellerTbody.innerHTML = dishes
      .map(
        (d, idx) => `
        <tr>
          <td><strong>#${idx + 1}</strong></td>
          <td>${escapeHtml(d.dish_name)}</td>
          <td>${d.total_quantity}</td>
          <td class="text-right"><strong>${formatMoney(d.total_revenue)}</strong></td>
        </tr>`
      )
      .join("");
  }

  const coupons = data.coupon_usages || [];
  if (coupons.length === 0) {
    couponUsageTbody.innerHTML = `<tr><td colspan="4" class="muted">Chưa có mã giảm giá nào.</td></tr>`;
  } else {
    couponUsageTbody.innerHTML = coupons
      .map(
        (c) => `
        <tr>
          <td><code>${escapeHtml(c.code)}</code></td>
          <td>${c.discount_type === "PERCENT" ? "Phần trăm" : "Tiền mặt"}</td>
          <td>${c.discount_type === "PERCENT" ? `${c.discount_value}%` : formatMoney(c.discount_value)}</td>
          <td class="text-right"><strong>${c.used_count}</strong></td>
        </tr>`
      )
      .join("");
  }
}

loadDashboardData();
