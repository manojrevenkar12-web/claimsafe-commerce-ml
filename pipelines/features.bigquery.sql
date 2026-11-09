WITH o AS (
  SELECT
    *,
    LEAD(day) OVER w AS next_day,
    LAG(day) OVER w AS prev_day,
    LAG(supply_days) OVER w AS prev_supply,
    ROW_NUMBER() OVER w AS n_this_product
  FROM commerce.orders
  WINDOW w AS (PARTITION BY customer, product ORDER BY day, order_id)
), hist AS (
  SELECT
    *,
    CAST(day - prev_day AS FLOAT64) / NULLIF(prev_supply, 0) AS last_ratio
  FROM o
)
SELECT
  order_id,
  customer,
  product,
  day,
  qty,
  supply_days,
  channel,
  price_eur,
  CAST(subscriber AS INT64) AS subscriber,
  CAST(promo AS INT64) AS promo,
  n_this_product,
  last_ratio,
  AVG(last_ratio) OVER (
    PARTITION BY customer
    ORDER BY day, order_id
    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
  ) AS customer_mean_ratio,
  COUNT(*) OVER (
    PARTITION BY customer
    ORDER BY day, order_id
    ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
  ) AS customer_prior_orders,
  MOD(CAST(FLOOR(day / 30) AS INT64), 12) AS month_of_year,
  next_day - day AS label_days,
  next_day AS label_known_day
FROM hist
