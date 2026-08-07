select
    segment,
    count(distinct customer_id) as customers
from {{ ref('customer_360') }}
group by segment
