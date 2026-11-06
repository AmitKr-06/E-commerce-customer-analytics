-- Delivery overview 
SELECT COUNT(*) AS delivered_orders,
       ROUND(AVG(order_delivered_customer_date > order_estimated_delivery_date) * 100, 2) AS late_rate_pct,
       ROUND(AVG(TIMESTAMPDIFF(SECOND, order_purchase_timestamp, order_delivered_customer_date)) / 86400, 2) AS avg_delivery_days,
       ROUND(AVG(TIMESTAMPDIFF(SECOND, order_purchase_timestamp, order_estimated_delivery_date)) / 86400, 2) AS avg_estimated_days
FROM valid_orders_t
WHERE order_status = 'delivered' AND order_delivered_customer_date IS NOT NULL;

-- Review score for late vs on-time orders 
SELECT CASE WHEN v.order_delivered_customer_date > v.order_estimated_delivery_date
            THEN 'late' ELSE 'on time or early' END AS delivery_status,
       COUNT(*) AS reviewed_orders,
       ROUND(AVG(r.review_score), 2) AS avg_review,
       ROUND(AVG(r.review_score = 1) * 100, 2) AS one_star_pct,
       ROUND(AVG(r.review_score = 5) * 100, 2) AS five_star_pct
FROM valid_orders_t v
JOIN latest_review_t r ON r.order_id = v.order_id
WHERE v.order_status = 'delivered' AND v.order_delivered_customer_date IS NOT NULL
GROUP BY delivery_status;

-- Review score by delay bucket (days versus the estimated date)
WITH d AS (
  SELECT v.order_id, r.review_score,
         TIMESTAMPDIFF(SECOND, v.order_estimated_delivery_date, v.order_delivered_customer_date) / 86400 AS delay_days
  FROM valid_orders_t v
  JOIN latest_review_t r ON r.order_id = v.order_id
  WHERE v.order_status = 'delivered' AND v.order_delivered_customer_date IS NOT NULL
)
SELECT CASE WHEN delay_days <= -7 THEN '1. early by 7+ days'
            WHEN delay_days <= 0 THEN '2. early by 0 to 7 days'
            WHEN delay_days <= 7 THEN '3. late by up to 7 days'
            ELSE '4. late by more than 7 days' END AS delay_bucket,
       COUNT(*) AS orders,
       ROUND(AVG(review_score), 2) AS avg_review,
       ROUND(AVG(review_score <= 2) * 100, 2) AS bad_review_pct
FROM d
GROUP BY delay_bucket
ORDER BY delay_bucket;

-- Delivery performance by customer state (100 or more orders, expect SP 8.76 days and 5.89 percent late)
SELECT v.customer_state,
       COUNT(*) AS orders,
       ROUND(AVG(TIMESTAMPDIFF(SECOND, v.order_purchase_timestamp, v.order_delivered_customer_date)) / 86400, 2) AS avg_delivery_days,
       ROUND(AVG(v.order_delivered_customer_date > v.order_estimated_delivery_date) * 100, 2) AS late_rate_pct,
       ROUND(AVG(r.review_score), 2) AS avg_review,
       RANK() OVER (ORDER BY AVG(v.order_delivered_customer_date > v.order_estimated_delivery_date) DESC) AS late_rank
FROM valid_orders_t v
LEFT JOIN latest_review_t r ON r.order_id = v.order_id
WHERE v.order_status = 'delivered' AND v.order_delivered_customer_date IS NOT NULL
GROUP BY v.customer_state
HAVING orders >= 100
ORDER BY late_rate_pct DESC;

-- Monthly late rate with 3-month moving average (Jan 2017 to Aug 2018)
WITH m AS (
  SELECT DATE_FORMAT(order_purchase_timestamp, '%Y-%m') AS order_month,
         COUNT(*) AS orders,
         AVG(order_delivered_customer_date > order_estimated_delivery_date) * 100 AS late_rate
  FROM valid_orders_t
  WHERE order_status = 'delivered' AND order_delivered_customer_date IS NOT NULL
    AND order_purchase_timestamp >= '2017-01-01' AND order_purchase_timestamp < '2018-09-01'
  GROUP BY order_month
)
SELECT order_month, orders, ROUND(late_rate, 2) AS late_rate_pct,
       ROUND(AVG(late_rate) OVER (ORDER BY order_month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2) AS moving_avg_3m
FROM m
ORDER BY order_month;

-- Extreme deliveries (more than 60 days, expect 306 in total)
SELECT COUNT(*) AS orders_over_60_days,
       ROUND(AVG(r.review_score), 2) AS avg_review
FROM valid_orders_t v
LEFT JOIN latest_review_t r ON r.order_id = v.order_id
WHERE v.order_status = 'delivered' AND v.order_delivered_customer_date IS NOT NULL
  AND TIMESTAMPDIFF(SECOND, v.order_purchase_timestamp, v.order_delivered_customer_date) / 86400 > 60;