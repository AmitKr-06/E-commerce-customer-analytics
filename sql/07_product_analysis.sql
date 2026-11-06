-- Top 10 categories by product revenue (expect health_beauty 1255560.16 first)
SELECT COALESCE(t.product_category_name_english, 'unknown') AS category,
       COUNT(*) AS items_sold,
       COUNT(DISTINCT i.order_id) AS orders,
       ROUND(SUM(i.price), 2) AS revenue,
       ROUND(AVG(i.price), 2) AS avg_price,
       ROUND(AVG(i.freight_value), 2) AS avg_freight,
       RANK() OVER (ORDER BY SUM(i.price) DESC) AS revenue_rank
FROM order_items i
JOIN valid_orders_t v ON v.order_id = i.order_id
JOIN products p ON p.product_id = i.product_id
LEFT JOIN category_translation t ON t.product_category_name = p.product_category_name
GROUP BY category
ORDER BY revenue DESC
LIMIT 10;

-- Number of categories that make up 80 percent of revenue (expect 18 of 74)
WITH cat AS (
  SELECT COALESCE(t.product_category_name_english, 'unknown') AS category, SUM(i.price) AS revenue
  FROM order_items i
  JOIN valid_orders_t v ON v.order_id = i.order_id
  JOIN products p ON p.product_id = i.product_id
  LEFT JOIN category_translation t ON t.product_category_name = p.product_category_name
  GROUP BY category
), shares AS (
  SELECT category, revenue,
         revenue / SUM(revenue) OVER () * 100 AS share_pct,
         SUM(revenue) OVER (ORDER BY revenue DESC) / SUM(revenue) OVER () * 100 AS cum_pct
  FROM cat
)
SELECT COUNT(*) AS total_categories,
       SUM(cum_pct - share_pct < 80) AS categories_for_80pct_revenue
FROM shares;

-- Category average review score (latest review, at least 200 orders)
SELECT COALESCE(t.product_category_name_english, 'unknown') AS category,
       COUNT(DISTINCT i.order_id) AS orders,
       ROUND(AVG(r.review_score), 2) AS avg_review
FROM order_items i
JOIN valid_orders_t v ON v.order_id = i.order_id
JOIN latest_review_t r ON r.order_id = i.order_id
JOIN products p ON p.product_id = i.product_id
LEFT JOIN category_translation t ON t.product_category_name = p.product_category_name
GROUP BY category
HAVING orders >= 200
ORDER BY avg_review ASC
LIMIT 10;

-- Best category in each customer state by revenue (top 3 states)
WITH x AS (
  SELECT v.customer_state,
         COALESCE(t.product_category_name_english, 'unknown') AS category,
         SUM(i.price) AS revenue
  FROM order_items i
  JOIN valid_orders_t v ON v.order_id = i.order_id
  JOIN products p ON p.product_id = i.product_id
  LEFT JOIN category_translation t ON t.product_category_name = p.product_category_name
  WHERE v.customer_state IN ('SP', 'RJ', 'MG')
  GROUP BY v.customer_state, category
), r AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY customer_state ORDER BY revenue DESC) AS rn FROM x
)
SELECT customer_state, category, ROUND(revenue, 2) AS revenue, rn AS category_rank
FROM r
WHERE rn <= 3
ORDER BY customer_state, rn;

-- Monthly revenue of the top 3 categories (Jan 2017 to Aug 2018)
WITH top3 AS (
  SELECT p.product_category_name
  FROM order_items i
  JOIN valid_orders_t v ON v.order_id = i.order_id
  JOIN products p ON p.product_id = i.product_id
  GROUP BY p.product_category_name
  ORDER BY SUM(i.price) DESC
  LIMIT 3
)
SELECT DATE_FORMAT(v.order_purchase_timestamp, '%Y-%m') AS order_month,
       COALESCE(t.product_category_name_english, 'unknown') AS category,
       ROUND(SUM(i.price), 2) AS revenue
FROM order_items i
JOIN valid_orders_t v ON v.order_id = i.order_id
JOIN products p ON p.product_id = i.product_id
JOIN top3 ON top3.product_category_name = p.product_category_name
LEFT JOIN category_translation t ON t.product_category_name = p.product_category_name
WHERE v.order_purchase_timestamp >= '2017-01-01' AND v.order_purchase_timestamp < '2018-09-01'
GROUP BY order_month, category
ORDER BY order_month, revenue DESC;