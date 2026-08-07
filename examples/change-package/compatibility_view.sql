CREATE OR REPLACE VIEW customer_360 AS
SELECT
    buyer_id,
    buyer_id AS customer_id,
    segment,
    lifetime_value
FROM customer_360_v2;
