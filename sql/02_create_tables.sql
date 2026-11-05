USE olist_ecommerce;

CREATE TABLE customers (
  customer_id CHAR(32) PRIMARY KEY,
  customer_unique_id CHAR(32) NOT NULL,
  customer_zip_code_prefix INT,
  customer_city VARCHAR(100),
  customer_state CHAR(2),
  INDEX idx_unique (customer_unique_id)
);

CREATE TABLE geolocation (
  geolocation_zip_code_prefix INT,
  geolocation_lat DOUBLE,
  geolocation_lng DOUBLE,
  geolocation_city VARCHAR(100),
  geolocation_state CHAR(2),
  INDEX idx_zip (geolocation_zip_code_prefix)
);

CREATE TABLE orders (
  order_id CHAR(32) PRIMARY KEY,
  customer_id CHAR(32) NOT NULL,
  order_status VARCHAR(20),
  order_purchase_timestamp DATETIME,
  order_approved_at DATETIME,
  order_delivered_carrier_date DATETIME,
  order_delivered_customer_date DATETIME,
  order_estimated_delivery_date DATETIME,
  INDEX idx_customer (customer_id),
  INDEX idx_purchase (order_purchase_timestamp)
);

CREATE TABLE order_items (
  order_id CHAR(32),
  order_item_id INT,
  product_id CHAR(32),
  seller_id CHAR(32),
  shipping_limit_date DATETIME,
  price DECIMAL(10,2),
  freight_value DECIMAL(10,2),
  PRIMARY KEY (order_id, order_item_id),
  INDEX idx_product (product_id),
  INDEX idx_seller (seller_id)
);

CREATE TABLE order_payments (
  order_id CHAR(32),
  payment_sequential INT,
  payment_type VARCHAR(20),
  payment_installments INT,
  payment_value DECIMAL(10,2),
  PRIMARY KEY (order_id, payment_sequential)
);

CREATE TABLE order_reviews (
  review_id CHAR(32),
  order_id CHAR(32),
  review_score TINYINT,
  review_comment_title VARCHAR(255),
  review_comment_message TEXT,
  review_creation_date DATETIME,
  review_answer_timestamp DATETIME,
  INDEX idx_order (order_id)
);

CREATE TABLE products (
  product_id CHAR(32) PRIMARY KEY,
  product_category_name VARCHAR(100),
  product_name_length DOUBLE,
  product_description_length DOUBLE,
  product_photos_qty DOUBLE,
  product_weight_g DOUBLE,
  product_length_cm DOUBLE,
  product_height_cm DOUBLE,
  product_width_cm DOUBLE
);

CREATE TABLE sellers (
  seller_id CHAR(32) PRIMARY KEY,
  seller_zip_code_prefix INT,
  seller_city VARCHAR(100),
  seller_state CHAR(2)
);

CREATE TABLE category_translation (
  product_category_name VARCHAR(100) PRIMARY KEY,
  product_category_name_english VARCHAR(100)
);

CREATE OR REPLACE VIEW v_valid_orders AS
SELECT o.order_id, o.customer_id, c.customer_unique_id, c.customer_state, c.customer_city,
       o.order_status, o.order_purchase_timestamp,
       o.order_delivered_customer_date, o.order_estimated_delivery_date,
       p.revenue
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
JOIN (SELECT order_id, SUM(payment_value) AS revenue
      FROM order_payments GROUP BY order_id) p ON p.order_id = o.order_id
WHERE o.order_status NOT IN ('canceled', 'unavailable')
  AND EXISTS (SELECT 1 FROM order_items i WHERE i.order_id = o.order_id);