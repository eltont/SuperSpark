-- Equivalent SQL for filter_project.py (tiny fixtures)
-- Register: CREATE TEMP VIEW orders USING json OPTIONS (path 'examples/fixtures/tiny/orders.jsonl');

SELECT
  order_id,
  customer_id,
  amount,
  region
FROM orders
WHERE amount > 50
  AND status = 'complete'
ORDER BY order_id;
