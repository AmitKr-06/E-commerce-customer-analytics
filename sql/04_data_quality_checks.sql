-- Data quality check --

-- Row count per table
SELECT 'customers' AS table_name, COUNT(*) AS row_count FROM customers
UNION ALL SELECT 'geolocation', COUNT(*) FROM geolocation
UNION ALL SELECT 'orders', COUNT(*) FROM orders
UNION ALL SELECT 'order_items', COUNT(*) FROM order_items
UNION ALL SELECT 'order_payments', COUNT(*) FROM order_payments
UNION ALL SELECT 'order_reviews', COUNT(*) FROM order_reviews
UNION ALL SELECT 'products', COUNT(*) FROM products
UNION ALL SELECT 'sellers', COUNT(*) FROM sellers
UNION ALL SELECT 'category_translation', COUNT(*) FROM category_translation;

-- Delivered orders with no delivery date (expect 8)
SELECT COUNT(*) AS delivered_no_date
FROM orders
WHERE order_status = 'delivered' AND order_delivered_customer_date IS NULL;

-- Orders without items, by status (expect 775 in total)
SELECT o.order_status, COUNT(*) AS orders_without_items
FROM orders o
LEFT JOIN order_items i ON i.order_id = o.order_id
WHERE i.order_id IS NULL
GROUP BY o.order_status
ORDER BY orders_without_items DESC;

-- Orders with more than one review (expect 547)
SELECT COUNT(*) AS orders_with_multiple_reviews
FROM (SELECT order_id FROM order_reviews GROUP BY order_id HAVING COUNT(*) > 1) t;

-- Payment total vs items plus freight (expect 98665 compared, 98276 exact, 249 over R$1)
WITH it AS (
  SELECT order_id, SUM(price + freight_value) AS items_total FROM order_items GROUP BY order_id
), pay AS (
  SELECT order_id, SUM(payment_value) AS pay_total FROM order_payments GROUP BY order_id
)
SELECT COUNT(*) AS orders_compared,
       SUM(ABS(pay.pay_total - it.items_total) <= 0.01) AS exact_match,
       SUM(ABS(pay.pay_total - it.items_total) > 1) AS mismatch_over_1
FROM it
JOIN pay ON pay.order_id = it.order_id;