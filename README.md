# Olist E-Commerce Data Cleaning Pipeline

A Python/pandas data cleaning project built on the Olist Brazilian
E-Commerce dataset (9 relational CSVs). Implements a **medallion
architecture** (bronze → silver → gold) ending in a small star schema
ready for analysis.

## Architecture

```
Bronze (data/)  --clean_*.py-->  Silver (silver/)  --build_gold.py-->  Gold (gold/)
   raw CSVs                    cleaned, validated                  dim_customers.csv
                                 1:1 with source                    dim_products.csv
                                                                     dim_sellers.csv
                                                                     fact_orders.csv
                                                                     fact_order_items.csv
```

- **Bronze** — the 9 raw CSVs, untouched.
- **Silver** — each raw table cleaned independently: nulls resolved
  (flagged, filled, or dropped based on *why* they're missing), text
  standardized, invalid values corrected or removed, keys verified.
- **Gold** — a star schema built from the cleaned silver tables: three
  dimension tables (`dim_customers`, `dim_products`, `dim_sellers`) and
  two fact tables at different grains (`fact_orders` — one row per
  order; `fact_order_items` — one row per order line item).

## Project structure

```
olist-cleaning/
├── data/                  # bronze: raw Olist CSVs
├── silver/                # cleaned output, one file per source table
├── gold/                  # dim_customers.csv, dim_products.csv, dim_sellers.csv,
│                          # fact_orders.csv, fact_order_items.csv
├── cleaning/              # one script per table, data -> silver
│   ├── clean_customers.py
│   ├── clean_geolocation.py
│   ├── clean_sellers.py
│   ├── clean_product_category.py
│   ├── clean_order_items.py
│   ├── clean_products.py
│   ├── clean_orders.py
│   ├── clean_order_payments.py
│   └── clean_reviews.py
├── build_gold.py          # silver -> gold: dim_customers, fact_orders
├── build_dim_products.py  # silver -> gold: dim_products
├── build_dim_sellers.py   # silver -> gold: dim_sellers
├── build_fact_order_items.py  # silver -> gold: fact_order_items
└── test_cleaning.py        # validation checks across silver + gold
```

## How to run

```bash
# 1. Activate the virtual environment
venv\Scripts\Activate.ps1        # Windows PowerShell
source venv/bin/activate         # Mac/Linux

# 2. Run each cleaning script (bronze -> silver)
python cleaning/clean_customers.py
python cleaning/clean_geolocation.py
python cleaning/clean_sellers.py
python cleaning/clean_product_category.py
python cleaning/clean_order_items.py
python cleaning/clean_products.py
python cleaning/clean_orders.py
python cleaning/clean_order_payments.py
python cleaning/clean_reviews.py

# 3. Build the gold layer (silver -> gold)
python build_gold.py
python build_dim_products.py
python build_dim_sellers.py
python build_fact_order_items.py

# 4. Validate everything
python test_cleaning.py
```

All scripts assume they're run from the project root, since file paths
inside them (`data/...`, `silver/...`, `gold/...`) are relative to the
current working directory, not the script's own location.

## Gold schema

**`dim_customers`** — one row per customer, enriched with geolocation
(city/state/lat/lng joined in via zip code prefix).

**`dim_products`** — one row per product, with English category name
joined in from the translation table (falls back to the Portuguese
name for the handful of categories missing from that table).

**`dim_sellers`** — one row per seller (city/state), purely descriptive.

**`fact_orders`** — one row per order (`order_id` matches the original
`orders` table 1:1), with:
- Order status and all 5 lifecycle dates
- `total_price`, `total_freight`, `n_items`, `n_unique_products`,
  `n_unique_sellers` (aggregated from order items)
- `total_payment_value`, `payment_types`, `n_payments` (aggregated
  from payments)
- `review_score`, `has_comment` (latest review per order)

**`fact_order_items`** — one row per order line item (`order_id`
matches the original `order_items` table 1:1 in row count), linked to
`dim_customers`, `dim_products`, and `dim_sellers`. This is the
correct grain for product- and seller-level analysis (e.g. "which
category sells best," "which sellers generate the most revenue") that
`fact_orders` alone can't answer, since an order can span multiple
products and sellers.

Two fact tables at two different grains, rather than forcing one table
to serve both order-level and item-level questions -- a standard
pattern in dimensional modeling (order header fact + order line fact).

## Key data issues found and how they were handled

| Table | Issue | Decision |
|---|---|---|
| customers | `zip_code_prefix` stored as int, dropping leading zeros (24% of rows) | Cast to string, `zfill(5)` |
| customers | `customer_unique_id` repeats (3,345 people with multiple orders) | Flagged (`is_repeat_customer`), not dropped — dropping would orphan real order history |
| geolocation | 26% exact duplicate rows | Dropped |
| geolocation | Accented/inconsistent city names (2,043 variants) | Normalized via Unicode NFKD decomposition |
| geolocation | Abbreviations & encoding corruption (`sp`, `rj`, `bh`, `sa£o paulo`) | Verified against `state` column, then manually mapped |
| geolocation | City/state mismatch (Rio de Janeiro city, Acre state) | Verified via coordinates + zip code, corrected the state |
| geolocation | 9,054 rows with coordinates outside Brazil | Dropped — no reliable way to recover the correct value |
| geolocation | ~1M GPS pings, not 1 row per location | Aggregated to one row per zip prefix (mean lat/lng) |
| sellers | Same zip and city issues as above | Same fixes applied |
| products | Typo in source column names (`_lenght`) | Renamed to `_length` |
| products | 610 rows missing all listing info | Flagged + filled category as `'unknown'` — dropping would have orphaned 1,603 real order items |
| products | 2 rows missing physical dimensions | Filled with column median |
| products | Rows with 0 dimensions | Dropped (physically impossible) — later surfaced 8 orphaned rows in `fact_order_items` (4 products, referenced by real sales); kept those sale records with a null product match rather than losing revenue data |
| product_category_translation | 13 real category names in `products` have no matching translation | Fell back to the Portuguese name instead of leaving the English column null |
| orders | Nulls in date columns | Mostly expected (tied to non-`delivered` statuses); 23 `delivered` orders missing a required date were flagged as inconsistent |
| order_items | `shipping_limit_date` stored as text | Converted to datetime |
| payments | `'not_defined'` payment type placeholder | Relabeled `'unknown'`, kept (dropping would silently remove 3 orders' only payment record) |
| payments | 2 rows with `payment_installments == 0` | Flagged and corrected to 1 (minimum valid value) |
| reviews | 814 duplicate `review_id`s | Kept most recent, dropped earlier duplicate |
| reviews | 58% missing review comments | Expected user behavior, not an error — flagged (`has_comment`), filled with `''` |
| reviews | 566 orders with more than one review | Flagged (`order_has_multiple_reviews`); latest review kept when merged into `fact_orders` |

## Testing

`test_cleaning.py` runs 60 automated checks across every table in both
the silver and gold layers — nulls, duplicate keys, valid ranges,
foreign key integrity, and confirmation that no merge step silently
duplicated or dropped rows. Run it after any change to the pipeline.

## Dataset

[Olist Brazilian E-Commerce Public Dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
— real (anonymized) orders from a Brazilian e-commerce marketplace,
2016-2018.
