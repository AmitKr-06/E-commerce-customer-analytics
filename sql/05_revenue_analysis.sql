-- Headline KPIs for valid sales (expect 98198 orders, revenue 15738221.95, AOV 160.27)
SELECT COUNT(*) AS valid_orders,
       COUNT(DISTINCT customer_unique_id) AS unique_customers,
       ROUND(SUM(revenue), 2) AS total_revenue,
       ROUND(AVG(revenue), 2) AS avg_order_value
FROM v_valid_orders;

-- Revenue of all paid orders vs valid sales (expect about 16008872 vs 15738222)
SELECT ROUND(SUM(p.revenue), 2) AS revenue_all_orders,
       ROUND(SUM(CASE WHEN v.order_id IS NOT NULL THEN p.revenue END), 2) AS revenue_valid_sales,
       ROUND(SUM(CASE WHEN v.order_id IS NULL THEN p.revenue END), 2) AS revenue_excluded
FROM (SELECT order_id, SUM(payment_value) AS revenue FROM order_payments GROUP BY order_id) p
LEFT JOIN v_valid_orders v ON v.order_id = p.order_id;

-- Monthly revenue with month-over-month growth and running total (Jan 2017 to Aug 2018)
WITH monthly AS (
  SELECT DATE_FORMAT(order_purchase_timestamp, '%Y-%m') AS order_month,
         COUNT(*) AS orders,
         ROUND(SUM(revenue), 2) AS revenue,
         ROUND(AVG(revenue), 2) AS aov
  FROM v_valid_orders
  WHERE order_purchase_timestamp >= '2017-01-01' AND order_purchase_timestamp < '2018-09-01'
  GROUP BY order_month
)
SELECT order_month, orders, revenue, aov,
       ROUND((revenue / LAG(revenue) OVER (ORDER BY order_month) - 1) * 100, 2) AS mom_pct,
       ROUND(SUM(revenue) OVER (ORDER BY order_month), 2) AS running_revenue
FROM monthly
ORDER BY order_month;

-- Top 5 months by revenue
WITH monthly AS (
  SELECT DATE_FORMAT(order_purchase_timestamp, '%Y-%m') AS order_month,
         ROUND(SUM(revenue), 2) AS revenue
  FROM v_valid_orders
  WHERE order_purchase_timestamp >= '2017-01-01' AND order_purchase_timestamp < '2018-09-01'
  GROUP BY order_month
)
SELECT order_month, revenue, RANK() OVER (ORDER BY revenue DESC) AS revenue_rank
FROM monthly
ORDER BY revenue_rank
LIMIT 5;

-- Orders and revenue by weekday (Monday = 0)
SELECT WEEKDAY(order_purchase_timestamp) AS weekday_no,
       DAYNAME(order_purchase_timestamp) AS weekday,
       COUNT(*) AS orders,
       ROUND(SUM(revenue), 2) AS revenue
FROM v_valid_orders
WHERE order_purchase_timestamp >= '2017-01-01' AND order_purchase_timestamp < '2018-09-01'
GROUP BY weekday_no, weekday
ORDER BY weekday_no;

-- Revenue by customer state with share of total (top 10)
SELECT customer_state,
       COUNT(*) AS orders,
       ROUND(SUM(revenue), 2) AS revenue,
       ROUND(SUM(revenue) / SUM(SUM(revenue)) OVER () * 100, 2) AS revenue_share_pct
FROM v_valid_orders
GROUP BY customer_state
ORDER BY revenue DESC
LIMIT 10;