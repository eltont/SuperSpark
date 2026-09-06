-- Equivalent SQL for joins.py (tiny fixtures)
-- CREATE TEMP VIEW orders USING json OPTIONS (path 'examples/fixtures/tiny/orders.jsonl');
-- CREATE TEMP VIEW customers USING json OPTIONS (path 'examples/fixtures/tiny/customers.jsonl');

SELECT
  o.order_id,
  o.customer_id,
  c.name,
  c.country,
  o.amount,
  o.region
FROM orders o
INNER JOIN customers c
  ON o.customer_id = c.customer_id
WHERE c.tier = 'gold'
  AND o.status = 'complete'
ORDER BY o.order_id;
