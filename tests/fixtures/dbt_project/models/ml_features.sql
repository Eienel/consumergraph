select
    customer_id,
    lifetime_value
from {{ ref('customer_360') }}
