-- Sellers with 30 or more delivered orders (expect 627 of 2970 sellers)
SELECT COUNT(*) AS sellers_30_plus_orders
FROM (SELECT i.seller_id
      FROM order_items i
      JOIN valid_orders_t v ON v.order_id = i.order_id
      WHERE v.order_status = 'delivered' AND v.order_delivered_customer_date IS NOT NULL
      GROUP BY i.seller_id
      HAVING COUNT(DISTINCT i.order_id) >= 30) t;

-- Sellers with the highest late rate (30 or more orders)
SELECT i.seller_id, s.seller_state,
       COUNT(DISTINCT i.order_id) AS orders,
       ROUND(AVG(v.order_delivered_customer_date > v.order_estimated_delivery_date) * 100, 2) AS late_rate_pct,
       ROUND(AVG(TIMESTAMPDIFF(SECOND, v.order_estimated_delivery_date, v.order_delivered_customer_date)) / 86400, 2) AS avg_delay_days,
       ROUND(SUM(i.price), 2) AS revenue
FROM order_items i
JOIN valid_orders_t v ON v.order_id = i.order_id
JOIN sellers s ON s.seller_id = i.seller_id
WHERE v.order_status = 'delivered' AND v.order_delivered_customer_date IS NOT NULL
GROUP BY i.seller_id, s.seller_state
HAVING orders >= 30
ORDER BY late_rate_pct DESC
LIMIT 10;

-- Sellers with late rate above 20 percent (expect 23)
WITH s AS (
  SELECT i.seller_id,
         COUNT(DISTINCT i.order_id) AS orders,
         AVG(v.order_delivered_customer_date > v.order_estimated_delivery_date) * 100 AS late_rate
  FROM order_items i
  JOIN valid_orders_t v ON v.order_id = i.order_id
  WHERE v.order_status = 'delivered' AND v.order_delivered_customer_date IS NOT NULL
  GROUP BY i.seller_id
  HAVING orders >= 30
)
SELECT COUNT(*) AS eligible_sellers,
       SUM(late_rate > 20) AS sellers_above_20pct,
       ROUND(AVG(late_rate), 2) AS avg_late_rate
FROM s;

-- Top 10 sellers by revenue with their late rate and cumulative revenue share
WITH s AS (
  SELECT i.seller_id,
         COUNT(DISTINCT i.order_id) AS orders,
         SUM(i.price) AS revenue,
         AVG(v.order_delivered_customer_date > v.order_estimated_delivery_date) * 100 AS late_rate
  FROM order_items i
  JOIN valid_orders_t v ON v.order_id = i.order_id
  WHERE v.order_status = 'delivered' AND v.order_delivered_customer_date IS NOT NULL
  GROUP BY i.seller_id
)
SELECT seller_id, orders, ROUND(revenue, 2) AS revenue, ROUND(late_rate, 2) AS late_rate_pct,
       RANK() OVER (ORDER BY revenue DESC) AS revenue_rank,
       ROUND(SUM(revenue) OVER (ORDER BY revenue DESC) / SUM(revenue) OVER () * 100, 2) AS cumulative_share_pct
FROM s
ORDER BY revenue DESC
LIMIT 10;

-- Seller performance by seller state (states with 100 or more orders)
SELECT s.seller_state,
       COUNT(DISTINCT i.order_id) AS orders,
       COUNT(DISTINCT i.seller_id) AS sellers,
       ROUND(AVG(v.order_delivered_customer_date > v.order_estimated_delivery_date) * 100, 2) AS late_rate_pct
FROM order_items i
JOIN valid_orders_t v ON v.order_id = i.order_id
JOIN sellers s ON s.seller_id = i.seller_id
WHERE v.order_status = 'delivered' AND v.order_delivered_customer_date IS NOT NULL
GROUP BY s.seller_state
HAVING orders >= 100
ORDER BY late_rate_pct DESC;