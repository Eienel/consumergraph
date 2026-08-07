SELECT COUNT(*) AS mismatches
FROM customer_360
WHERE customer_id IS DISTINCT FROM buyer_id;
