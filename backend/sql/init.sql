-- Tạo database food_night_db + các bảng + dữ liệu mẫu.
-- Cách chạy bằng MySQL Workbench:
--   File > Open SQL Script... > chọn file này > bấm nút tia sét (Execute) > Refresh ô SCHEMAS.

SET NAMES utf8mb4;

CREATE DATABASE IF NOT EXISTS food_night_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE food_night_db;

-- Bảng mẫu items (giữ lại để kiểm tra kết nối cơ bản)
CREATE TABLE IF NOT EXISTS items (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  name        VARCHAR(255) NOT NULL,
  description TEXT NULL,
  price       DECIMAL(12, 2) NOT NULL DEFAULT 0,
  created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 1. Bảng người dùng (users)
CREATE TABLE IF NOT EXISTS users (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  full_name     VARCHAR(100) NOT NULL,
  email         VARCHAR(150) NOT NULL UNIQUE,
  phone         VARCHAR(20) NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role          VARCHAR(30) NOT NULL DEFAULT 'CUSTOMER',
  is_active     TINYINT(1) NOT NULL DEFAULT 1,
  created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Bảng danh mục món ăn (categories)
CREATE TABLE IF NOT EXISTS categories (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  name        VARCHAR(100) NOT NULL UNIQUE,
  description TEXT NULL,
  is_active   TINYINT(1) NOT NULL DEFAULT 1,
  created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. Bảng món ăn (dishes)
CREATE TABLE IF NOT EXISTS dishes (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  category_id  INT NULL,
  name         VARCHAR(255) NOT NULL,
  description  TEXT NULL,
  price        DECIMAL(15, 2) NOT NULL DEFAULT 0,
  image_url    VARCHAR(500) NULL,
  is_available TINYINT(1) NOT NULL DEFAULT 1,
  is_active    TINYINT(1) NOT NULL DEFAULT 1,
  status       VARCHAR(30) NOT NULL DEFAULT 'AVAILABLE',
  created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_dishes_category FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. Bảng tùy chọn món ăn (dish_options)
CREATE TABLE IF NOT EXISTS dish_options (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  dish_id      INT NOT NULL,
  name         VARCHAR(100) NOT NULL,
  price        DECIMAL(15, 2) NOT NULL DEFAULT 0,
  is_available TINYINT(1) NOT NULL DEFAULT 1,
  created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_dish_options_dish FOREIGN KEY (dish_id) REFERENCES dishes(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. Bảng khu vực giao hàng (delivery_areas)
CREATE TABLE IF NOT EXISTS delivery_areas (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  name         VARCHAR(150) NOT NULL UNIQUE,
  shipping_fee DECIMAL(15, 2) NOT NULL DEFAULT 0,
  is_active    TINYINT(1) NOT NULL DEFAULT 1,
  created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. Bảng giỏ hàng (carts) & chi tiết giỏ hàng (cart_items)
CREATE TABLE IF NOT EXISTS carts (
  id         INT AUTO_INCREMENT PRIMARY KEY,
  user_id    INT NOT NULL UNIQUE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_carts_user FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS cart_items (
  id               INT AUTO_INCREMENT PRIMARY KEY,
  cart_id          INT NOT NULL,
  dish_id          INT NOT NULL,
  selected_options JSON NULL,
  note             VARCHAR(500) NULL,
  quantity         INT NOT NULL DEFAULT 1,
  created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_cart_items_cart FOREIGN KEY (cart_id) REFERENCES carts(id) ON DELETE CASCADE,
  CONSTRAINT fk_cart_items_dish FOREIGN KEY (dish_id) REFERENCES dishes(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. Bảng đơn hàng (orders) & chi tiết đơn hàng (order_items)
CREATE TABLE IF NOT EXISTS orders (
  id                  INT AUTO_INCREMENT PRIMARY KEY,
  order_code          VARCHAR(30) NOT NULL UNIQUE,
  user_id             INT NOT NULL,
  recipient_name      VARCHAR(100) NOT NULL,
  recipient_phone     VARCHAR(20) NOT NULL,
  delivery_address    VARCHAR(500) NOT NULL,
  delivery_area_id    INT NOT NULL,
  shipping_fee        DECIMAL(15, 2) NOT NULL DEFAULT 0,
  discount_amount     DECIMAL(15, 2) NOT NULL DEFAULT 0,
  subtotal            DECIMAL(15, 2) NOT NULL,
  total_amount        DECIMAL(15, 2) NOT NULL,
  payment_method      VARCHAR(30) NOT NULL,
  desired_delivery_at DATETIME NULL,
  status              VARCHAR(30) NOT NULL DEFAULT 'PENDING',
  created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  CONSTRAINT fk_orders_user FOREIGN KEY (user_id) REFERENCES users(id),
  CONSTRAINT fk_orders_area FOREIGN KEY (delivery_area_id) REFERENCES delivery_areas(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS order_items (
  id               INT AUTO_INCREMENT PRIMARY KEY,
  order_id         INT NOT NULL,
  dish_id          INT NULL,
  dish_name        VARCHAR(255) NOT NULL,
  dish_price       DECIMAL(15, 2) NOT NULL,
  selected_options JSON NULL,
  options_price    DECIMAL(15, 2) NOT NULL DEFAULT 0,
  note             VARCHAR(500) NULL,
  quantity         INT NOT NULL,
  line_total       DECIMAL(15, 2) NOT NULL,
  created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_order_items_order FOREIGN KEY (order_id) REFERENCES orders(id),
  CONSTRAINT fk_order_items_dish FOREIGN KEY (dish_id) REFERENCES dishes(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- DỮ LIỆU MẪU ĐỂ TEST API GIỎ HÀNG & ĐẶT MÓN
-- ============================================================
INSERT IGNORE INTO users (id, full_name, email, phone, password_hash, role, is_active) VALUES
  (1, 'Thái Nguyễn Gia Bảo', 'giabao@example.com', '0901234567', 'hashed_pw_1', 'CUSTOMER', 1),
  (2, 'Nguyễn Văn B', 'vanb@example.com', '0902345678', 'hashed_pw_2', 'CUSTOMER', 1);

INSERT IGNORE INTO categories (id, name, description, is_active) VALUES
  (1, 'Món chính đêm', 'Các món ăn no giao đêm', 1),
  (2, 'Đồ uống', 'Trà, nước giải khát', 1);

INSERT IGNORE INTO dishes (id, category_id, name, description, price, is_available, is_active, status) VALUES
  (1, 1, 'Mì trộn Indomie đặc biệt', 'Mì trộn kèm trứng lòng đào và xúc xích', 45000, 1, 1, 'AVAILABLE'),
  (2, 1, 'Cơm gà xối mỡ (Hết hàng)', 'Món dùng để test chặn món hết hàng', 55000, 0, 1, 'OUT_OF_STOCK'),
  (3, 1, 'Cháo sườn sụn (Món ẩn)', 'Món dùng để test chặn món bị ẩn', 35000, 1, 0, 'HIDDEN');

INSERT IGNORE INTO dish_options (id, dish_id, name, price, is_available) VALUES
  (1, 1, 'Thêm trứng lòng đào', 7000, 1),
  (2, 1, 'Thêm phô mai kéo sợi', 10000, 1),
  (3, 1, 'Topping tóp mỡ (Đã hết)', 5000, 0);

INSERT IGNORE INTO delivery_areas (id, name, shipping_fee, is_active) VALUES
  (1, 'Quận Hà Đông', 15000, 1),
  (2, 'Quận Thanh Xuân', 20000, 1);
-- 8. Bảng lịch sử trạng thái đơn hàng (order_status_histories)
CREATE TABLE IF NOT EXISTS order_status_histories (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  order_id    INT NOT NULL,
  old_status  VARCHAR(30) NULL,
  new_status  VARCHAR(30) NOT NULL,
  changed_by  INT NULL,
  note        VARCHAR(500) NULL,
  created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_status_histories_order FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
  CONSTRAINT fk_status_histories_user FOREIGN KEY (changed_by) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Bổ sung thứ tự danh mục
ALTER TABLE categories
ADD COLUMN sort_order INT NOT NULL DEFAULT 0;

-- Bổ sung đánh dấu món nổi bật
ALTER TABLE dishes
ADD COLUMN is_featured TINYINT(1) NOT NULL DEFAULT 0;

-- Bổ sung thông tin nhóm tùy chọn
ALTER TABLE dish_options
ADD COLUMN group_name VARCHAR(100) NOT NULL DEFAULT 'Topping',
ADD COLUMN is_required TINYINT(1) NOT NULL DEFAULT 0,
ADD COLUMN allow_multiple TINYINT(1) NOT NULL DEFAULT 0;
-- 1. Thêm 6 danh mục
INSERT INTO categories (name, description, sort_order, is_active)
SELECT v.name, v.description, v.sort_order, 1
FROM (
    SELECT 'Mì và đồ ăn nhanh' AS name,
           'Các món mì và đồ ăn nhanh' AS description, 1 AS sort_order
    UNION ALL
    SELECT 'Cơm và món no', 'Các món cơm và món ăn chính', 2
    UNION ALL
    SELECT 'Đồ ăn vặt', 'Các món ăn nhẹ và ăn vặt', 3
    UNION ALL
    SELECT 'Đồ chiên', 'Các món chiên giòn', 4
    UNION ALL
    SELECT 'Đồ uống', 'Nước uống và giải khát', 5
    UNION ALL
    SELECT 'Ăn đêm đặc biệt', 'Các món đặc biệt dành cho buổi tối', 6
) AS v
WHERE NOT EXISTS (
    SELECT 1 FROM categories c WHERE c.name = v.name
);

-- 2. Thêm 30 món
INSERT INTO dishes (
    category_id, name, description, price,
    image_url, is_available, is_active,
    status, is_featured
)
SELECT
    c.id, v.name, v.description, v.price,
    NULL, 1, 1, 'AVAILABLE', v.is_featured
FROM (
    SELECT 'Mì và đồ ăn nhanh' AS category_name,
           'Mì trộn Indomie' AS name,
           'Mì trộn sốt đặc biệt' AS description,
           35000 AS price, 1 AS is_featured
    UNION ALL SELECT 'Mì và đồ ăn nhanh', 'Mì cay hải sản', 'Mì cay cùng hải sản', 55000, 1
    UNION ALL SELECT 'Mì và đồ ăn nhanh', 'Mì xào bò', 'Mì xào thịt bò', 45000, 0
    UNION ALL SELECT 'Mì và đồ ăn nhanh', 'Mì trộn xúc xích', 'Mì trộn xúc xích và rau', 40000, 0
    UNION ALL SELECT 'Mì và đồ ăn nhanh', 'Mì tương đen', 'Mì sốt tương đen Hàn Quốc', 45000, 0

    UNION ALL SELECT 'Cơm và món no', 'Cơm gà xối mỡ', 'Cơm gà chiên giòn', 55000, 1
    UNION ALL SELECT 'Cơm và món no', 'Cơm rang dưa bò', 'Cơm rang với thịt bò và dưa chua', 50000, 0
    UNION ALL SELECT 'Cơm và món no', 'Cơm sườn nướng', 'Cơm sườn nướng mật ong', 55000, 1
    UNION ALL SELECT 'Cơm và món no', 'Cơm chiên trứng', 'Cơm chiên trứng đơn giản', 35000, 0
    UNION ALL SELECT 'Cơm và món no', 'Cơm bò lúc lắc', 'Cơm ăn kèm bò lúc lắc', 60000, 0

    UNION ALL SELECT 'Đồ ăn vặt', 'Bánh tráng trộn', 'Bánh tráng trộn đầy đủ topping', 25000, 1
    UNION ALL SELECT 'Đồ ăn vặt', 'Xúc xích nướng', 'Xúc xích nướng ăn kèm tương', 15000, 0
    UNION ALL SELECT 'Đồ ăn vặt', 'Cá viên chiên', 'Cá viên chiên giòn', 30000, 0
    UNION ALL SELECT 'Đồ ăn vặt', 'Khoai tây lắc phô mai', 'Khoai tây chiên lắc phô mai', 35000, 1
    UNION ALL SELECT 'Đồ ăn vặt', 'Phô mai que', 'Phô mai que chiên giòn', 30000, 0

    UNION ALL SELECT 'Đồ chiên', 'Gà rán truyền thống', 'Gà rán giòn', 40000, 1
    UNION ALL SELECT 'Đồ chiên', 'Cánh gà chiên nước mắm', 'Cánh gà chiên nước mắm', 50000, 0
    UNION ALL SELECT 'Đồ chiên', 'Đùi gà chiên giòn', 'Đùi gà tẩm bột chiên', 45000, 0
    UNION ALL SELECT 'Đồ chiên', 'Tôm chiên xù', 'Tôm tẩm bột chiên xù', 55000, 0
    UNION ALL SELECT 'Đồ chiên', 'Mực chiên giòn', 'Mực tẩm bột chiên giòn', 60000, 1

    UNION ALL SELECT 'Đồ uống', 'Trà đào cam sả', 'Trà đào cam sả mát lạnh', 30000, 1
    UNION ALL SELECT 'Đồ uống', 'Trà tắc', 'Trà tắc giải khát', 15000, 0
    UNION ALL SELECT 'Đồ uống', 'Coca Cola', 'Nước ngọt Coca Cola', 15000, 0
    UNION ALL SELECT 'Đồ uống', 'Nước cam ép', 'Nước cam ép tươi', 25000, 0
    UNION ALL SELECT 'Đồ uống', 'Trà sữa truyền thống', 'Trà sữa vị truyền thống', 30000, 1

    UNION ALL SELECT 'Ăn đêm đặc biệt', 'Cháo sườn sụn', 'Cháo sườn sụn nóng', 35000, 1
    UNION ALL SELECT 'Ăn đêm đặc biệt', 'Bánh mì bò sốt vang', 'Bánh mì ăn cùng bò sốt vang', 45000, 0
    UNION ALL SELECT 'Ăn đêm đặc biệt', 'Lẩu tokbokki mini', 'Lẩu tokbokki Hàn Quốc', 65000, 1
    UNION ALL SELECT 'Ăn đêm đặc biệt', 'Bún trộn thịt nướng', 'Bún trộn thịt nướng và rau', 45000, 0
    UNION ALL SELECT 'Ăn đêm đặc biệt', 'Mì Ý sốt bò bằm', 'Mì Ý sốt bò bằm', 55000, 0
) AS v
JOIN categories c ON c.name = v.category_name
WHERE NOT EXISTS (
    SELECT 1
    FROM dishes d
    WHERE d.category_id = c.id
      AND d.name = v.name
);