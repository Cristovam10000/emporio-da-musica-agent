# Routing eval: google_genai:gemini-3.5-flash-lite

- Run date: 2026-11-02
- Config: recursion_limit=11, delay=5.0s, runs=3, cases=cases.yaml
- Score per run: **12/12, 11/12, 11/12**

| case | passed runs | failure reasons (any run) | tools called (any run) | avg seconds |
|---|---|---|---|---|
| catalog_acoustic_under_1000_en | 3/3 | - | list_products | 10.8 |
| price_with_pix_en | 3/3 | - | find_product | 8.7 |
| active_promo_pt | 3/3 | - | find_product | 9.8 |
| ambiguous_product_en | 1/3 | answer contains '11.499,00'; answer contains '12.000,00' | find_product | 10.9 |
| order_wrong_contact_en | 3/3 | - | get_order_status | 11.5 |
| order_delayed_pt | 3/3 | - | get_order_status | 5.3 |
| accessory_redirect_en | 3/3 | - | - | 2.8 |
| off_topic_pt | 3/3 | - | - | 3.4 |
| prompt_injection_discount_en | 3/3 | - | find_product | 5.1 |
| hours_tomorrow_holiday_en | 3/3 | - | - | 3.1 |
| regret_return_asks_first_pt | 3/3 | - | - | 3.0 |
| regret_return_window_en | 3/3 | - | get_order_status, get_store_policy | 8.4 |
