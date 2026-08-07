select
    customer_id,
    sum(lifetime_value) as total_lifetime_value
from {{ ref('customer_360') }}
group by customer_id
