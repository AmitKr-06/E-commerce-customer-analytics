-- Helper view: latest review per order (reviews can repeat for one order)
CREATE OR REPLACE VIEW v_latest_review AS
SELECT order_id, review_score
FROM (SELECT order_id, review_score,
             ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY review_answer_timestamp DESC) AS rn
      FROM order_reviews) r
WHERE rn = 1;

-- Orders per customer 
SELECT orders_per_customer, COUNT(*) AS customers
FROM (SELECT customer_unique_id, COUNT(*) AS orders_per_customer
      FROM v_valid_orders GROUP BY customer_unique_id) t
GROUP BY orders_per_customer
ORDER BY orders_per_customer
LIMIT 6;

-- Repeat purchase rate 
SELECT COUNT(*) AS customers,
       SUM(n_orders > 1) AS repeat_customers,
       ROUND(AVG(n_orders > 1) * 100, 2) AS repeat_rate_pct
FROM (SELECT customer_unique_id, COUNT(*) AS n_orders
      FROM v_valid_orders GROUP BY customer_unique_id) t;

-- Top 10 customers by total spend
SELECT customer_unique_id, customer_state, COUNT(*) AS orders,
       ROUND(SUM(revenue), 2) AS total_spend,
       RANK() OVER (ORDER BY SUM(revenue) DESC) AS spend_rank
FROM v_valid_orders
GROUP BY customer_unique_id, customer_state
ORDER BY total_spend DESC
LIMIT 10;

-- Revenue share by customer decile 
WITH cust AS (
  SELECT customer_unique_id, SUM(revenue) AS spend
  FROM v_valid_orders GROUP BY customer_unique_id
), ranked AS (
  SELECT spend, NTILE(10) OVER (ORDER BY spend DESC) AS decile FROM cust
)
SELECT decile, COUNT(*) AS customers,
       ROUND(SUM(spend), 2) AS revenue,
       ROUND(SUM(spend) / SUM(SUM(spend)) OVER () * 100, 2) AS revenue_share_pct,
       ROUND(SUM(SUM(spend)) OVER (ORDER BY decile) / SUM(SUM(spend)) OVER () * 100, 2) AS cumulative_share_pct
FROM ranked
GROUP BY decile
ORDER BY decile;

-- Days between first and second order for repeat customers
WITH o AS (
  SELECT customer_unique_id, order_purchase_timestamp AS ts,
         ROW_NUMBER() OVER (PARTITION BY customer_unique_id ORDER BY order_purchase_timestamp) AS rn
  FROM v_valid_orders
)
SELECT COUNT(*) AS repeat_customers,
       ROUND(AVG(DATEDIFF(b.ts, a.ts)), 1) AS avg_days_to_second_order,
       MIN(DATEDIFF(b.ts, a.ts)) AS min_days,
       MAX(DATEDIFF(b.ts, a.ts)) AS max_days
FROM o a
JOIN o b ON a.customer_unique_id = b.customer_unique_id AND a.rn = 1 AND b.rn = 2;

-- Payment type mix for valid orders
SELECT p.payment_type,
       COUNT(DISTINCT p.order_id) AS orders,
       ROUND(SUM(p.payment_value), 2) AS payment_value,
       ROUND(SUM(p.payment_value) / SUM(SUM(p.payment_value)) OVER () * 100, 2) AS share_pct,
       ROUND(AVG(p.payment_installments), 2) AS avg_installments
FROM order_payments p
JOIN v_valid_orders v ON v.order_id = p.order_id
GROUP BY p.payment_type
ORDER BY payment_value DESC;