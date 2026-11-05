-- Data quality check --

-- Row count per table --

SELECT 'customers' AS table_name, COUNT(*) AS row_count FROM customers

UNION ALL SELECT 'geolocation', COUNT(*) FROM geolocation
UNION ALL SELECT 'orders', COUNT(*) FROM orders
UNION ALL SELECT 'order_items', COUNT(*) FROM order_items
UNION ALL SELECT 'order_payments', COUNT(*) FROM order_payments
UNION ALL SELECT 'order_reviews', COUNT(*) FROM order_reviews
UNION ALL SELECT 'products', COUNT(*) FROM products
UNION ALL SELECT 'sellers', COUNT(*) FROM sellers
UNION ALL SELECT 'category_translation', COUNT(*) FROM category_translation;

-- Delivered orders with no delivery date 
SELECT COUNT(*) AS delivery_no_date
FROM orders
WHERE order_status = 'delivered' AND order_delivered_customer_data IS NULL;

-- Orders without items, by status 
SELECT o.orders_satus, COUNT(*) AS orders_without_items
FROM orders o
LEFT JOIN order_items i ON i.order_id = o.order_id
WHERE i.order_id IS NULL
GROUP BY o.order_status
ORDER BY orders_without_items DESC;

-- Orders with more than one review
SELECT COUNT(*) AS order_with_multiple_reviews
FROM (SELECT order_id FROM order_reviews GROUP BY order_id HAVING COUNT(*) > 1) t;

-- Payment total vs items plus freight
WITH it AS (
    SELECT order_id, SUM(price + freight_value) AS items_total FROM order_items GROUP BY order_id
), pay AS (
    SELECT order_id, SUM(payment_value) AS pay_total FROM order_payments GROUP BY order_id
)

SELECT COUNT(*) AS order_compared,
       SUM(ABS(pay.pay_toatl - it.items_toatl) <= 0.01) AS exact_match,
       SUM(ABS(pay.pay_toatl - it.items_total) > 1) AS mismatch_over_1
FROM it
JOIN pay ON pay.order_id = it.order_id;