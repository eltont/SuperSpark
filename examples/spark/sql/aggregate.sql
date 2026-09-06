-- Equivalent SQL for aggregate.py (tiny fixtures)
-- CREATE TEMP VIEW orders USING json OPTIONS (path 'examples/fixtures/tiny/orders.jsonl');

SELECT
  region,
  COUNT(*) AS order_count,
  ROUND(SUM(amount), 2) AS amount_sum,
  ROUND(AVG(amount), 4) AS amount_avg
FROM orders
WHERE status <> 'cancelled'
GROUP BY region
ORDER BY region;
