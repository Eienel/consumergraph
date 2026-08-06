select
    customer_id,
    segment
from {{ ref('customer_360') }}
where segment = 'at_risk'
