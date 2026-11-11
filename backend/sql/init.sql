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
