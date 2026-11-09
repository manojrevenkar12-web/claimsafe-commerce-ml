"""Point-in-time features in SQL, run in DuckDB here and transpiled to BigQuery for production.

Every feature of an order uses only what was known when the order was placed. The label (days until the same
customer reorders the same product) becomes known on the day of that next order, which is when monitoring may use it.
"""

from __future__ import annotations

import logging

import duckdb
import pandas as pd
import sqlglot

logging.getLogger("sqlglot").setLevel(logging.ERROR)

FEATURES_SQL = """
WITH o AS (
  SELECT *,
    LEAD(day) OVER w AS next_day,
    LAG(day) OVER w AS prev_day,
    LAG(supply_days) OVER w AS prev_supply,
    ROW_NUMBER() OVER w AS n_this_product
  FROM orders
  WINDOW w AS (PARTITION BY customer, product ORDER BY day, order_id)
),
hist AS (
  SELECT *, CAST(day - prev_day AS DOUBLE) / NULLIF(prev_supply, 0) AS last_ratio
  FROM o
)
SELECT
  order_id, customer, product, day, qty, supply_days, channel, price_eur,
  CAST(subscriber AS INTEGER) AS subscriber,
  CAST(promo AS INTEGER) AS promo,
  n_this_product,
  last_ratio,
  AVG(last_ratio) OVER (PARTITION BY customer ORDER BY day, order_id
                        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS customer_mean_ratio,
  COUNT(*) OVER (PARTITION BY customer ORDER BY day, order_id
                 ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS customer_prior_orders,
  CAST(FLOOR(day / 30) AS INTEGER) % 12 AS month_of_year,
  next_day - day AS label_days,
  next_day AS label_known_day
FROM hist
"""

NUMERIC = [
    "qty",
    "supply_days",
    "price_eur",
    "subscriber",
    "promo",
    "n_this_product",
    "last_ratio",
    "customer_mean_ratio",
    "customer_prior_orders",
    "month_of_year",
]
CATEGORICAL = ["channel", "product"]


def build(orders: pd.DataFrame, con: duckdb.DuckDBPyConnection | None = None) -> pd.DataFrame:
    con = con or duckdb.connect()
    con.register("orders", orders)
    df = con.execute(FEATURES_SQL).df()
    con.unregister("orders")
    return df.sort_values(["day", "order_id"]).reset_index(drop=True)


def bigquery_sql(dataset: str = "commerce") -> str:
    """The same feature query in BigQuery Standard SQL, reading from `<dataset>.orders`."""
    sql = FEATURES_SQL.replace("FROM orders", f"FROM {dataset}.orders")
    out = sqlglot.transpile(sql, read="duckdb", write="bigquery", pretty=True)[0]
    # The ordering keys are never null, so DuckDB's explicit NULLS LAST carries no meaning in BigQuery.
    return out.replace(" NULLS LAST", "") + "\n"
