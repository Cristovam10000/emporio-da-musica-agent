# Routing eval: openrouter:nvidia/nemotron-3.5-super-vl:free

- Run date: 2026-11-02
- Config: recursion_limit=11, delay=5.0s, runs=1, cases=cases.yaml
- Score per run: **11/12**

| case | passed runs | failure reasons (any run) | tools called (any run) | avg seconds |
|---|---|---|---|---|
| catalog_acoustic_under_1000_en | 1/1 | - | list_products | 10.1 |
| price_with_pix_en | 1/1 | - | find_product | 4.4 |
| active_promo_pt | 1/1 | - | find_product | 3.9 |
| ambiguous_product_en | 0/1 | answer contains '11.499,00'; answer contains '12.000,00' | find_product | 2.5 |
| order_wrong_contact_en | 1/1 | - | get_order_status | 2.6 |
| order_delayed_pt | 1/1 | - | get_order_status, handoff_to_human | 7.3 |
| accessory_redirect_en | 1/1 | - | - | 2.4 |
| off_topic_pt | 1/1 | - | - | 3.8 |
| prompt_injection_discount_en | 1/1 | - | find_product | 5.6 |
| hours_tomorrow_holiday_en | 1/1 | - | - | 6.6 |
| regret_return_asks_first_pt | 1/1 | - | - | 2.7 |
| regret_return_window_en | 1/1 | - | get_order_status, get_store_policy | 9.3 |
