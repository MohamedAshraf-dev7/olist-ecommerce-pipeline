# Olist E-Commerce Data Pipeline

An end-to-end data engineering pipeline built on the Olist Brazilian
E-Commerce dataset (9 relational CSVs). Implements a **medallion
architecture** (bronze → silver → gold), orchestrated with **Airflow**,
loaded into a **Postgres** warehouse, and visualized in **Metabase**.

## Architecture

```
CSV Data → Python (clean) → Airflow (orchestrate) → Postgres (warehouse) → Metabase (dashboard)
```

```
Bronze (bronze/) --clean_*.py--> Silver (silver/) --build_gold.py--> Gold (gold/) --load_to_warehouse.py--> Postgres --> Metabase
   raw CSVs                    cleaned, validated                 star schema                            queryable        dashboards
                                 1:1 with source                   (5 tables)                              warehouse
```

The whole flow above is triggered by a single Airflow DAG
(`olist_medallion_pipeline`): 9 parallel cleaning tasks → one gold-build
task → warehouse load → automated tests, all running inside Docker.

- **Bronze** — the 9 raw CSVs, untouched.
- **Silver** — each raw table cleaned independently: nulls resolved
  (flagged, filled, or dropped based on *why* they're missing), text
  standardized, invalid values corrected or removed, keys verified.
- **Gold** — a star schema built from the cleaned silver tables: three
  dimension tables (`dim_customers`, `dim_products`, `dim_sellers`) and
  two fact tables at different grains (`fact_orders` — one row per
  order; `fact_order_items` — one row per order line item).
- **Orchestration** — Apache Airflow (Docker), running the full
  bronze → silver → gold → warehouse flow as one DAG, on demand.
- **Warehouse** — Postgres, loaded from the gold-layer CSVs, queryable
  directly by SQL or a BI tool.
- **Dashboard** — Metabase, connected to the Postgres warehouse.

## Project structure

This project spans two folders: the data pipeline itself, and the
Airflow orchestration layer that runs it.

```
e-commerce/                    # the data pipeline
├── bronze/                    # raw Olist CSVs (not tracked in git)
├── silver/                    # cleaned output, one file per source table
├── gold/                      # dim_customers.csv, dim_products.csv, dim_sellers.csv,
│                               # fact_orders.csv, fact_order_items.csv
├── cleaning/                  # one script per table, bronze -> silver
│   ├── clean_customers_info.py
│   ├── clean_geolocation.py
│   ├── clean_sellers_info.py
│   ├── clean_product_category.py
│   ├── clean_order_items.py
│   ├── clean_product_info.py
│   ├── clean_orders_info.py
│   ├── clean_order_payments.py
│   └── clean_order_reviews.py
├── analysis/                  # charts produced by analyze_gold.py
├── build_gold.py              # silver -> gold: all 5 star schema tables
├── load_to_warehouse.py       # gold CSVs -> Postgres warehouse
├── analyze_gold.py            # sample analysis / charts against the gold layer
├── test_cleaning.py           # validation checks across silver + gold
├── requirements.txt
└── README.md

airflow-olist/                 # the orchestration layer
├── docker-compose.yaml        # airflow + postgres (warehouse) + metabase
├── dags/
│   └── olist_pipeline.py      # the DAG: silver tasks -> build_gold -> load -> tests
├── logs/
├── plugins/
├── config/
└── .env
```

`airflow-olist` mounts `e-commerce` as a volume, so the DAG can call
the pipeline's actual scripts directly — no code duplication between
the two folders.

## How to run

### Option A — via Airflow (recommended, fully orchestrated)

```bash
cd airflow-olist
docker compose up -d
```

Wait for all 3 containers (`airflow`, `warehouse`, `metabase`) to report
`Up`, then open `http://localhost:8080`, log in, and trigger the
`olist_medallion_pipeline` DAG. This runs the entire flow — all 9
silver cleaning tasks, the gold build, the warehouse load, and the
test suite — end to end.

### Option B — manually, step by step

```bash
cd e-commerce

# 1. Activate the virtual environment
venv\Scripts\Activate.ps1        # Windows PowerShell
source venv/bin/activate         # Mac/Linux

# 2. Run each cleaning script (bronze -> silver)
python cleaning/clean_customers_info.py
python cleaning/clean_geolocation.py
python cleaning/clean_sellers_info.py
python cleaning/clean_product_category.py
python cleaning/clean_order_items.py
python cleaning/clean_product_info.py
python cleaning/clean_orders_info.py
python cleaning/clean_order_payments.py
python cleaning/clean_order_reviews.py

# 3. Build the gold layer (silver -> gold)
python build_gold.py

# 4. Load into the Postgres warehouse
python load_to_warehouse.py

# 5. Validate everything
python test_cleaning.py

# 6. (optional) Generate sample analysis charts
python analyze_gold.py
```

All scripts assume they're run from the `e-commerce` project root,
since file paths inside them (`bronze/...`, `silver/...`, `gold/...`)
are relative to the current working directory, not the script's own
location.

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

## Orchestration

The entire pipeline runs as a single Airflow DAG, `olist_medallion_pipeline`:

```
clean_customers ─┐
clean_geolocation├─┐
clean_sellers    │ │
clean_*  (9 total)├─▶ build_gold ─▶ load_to_warehouse ─▶ run_tests
                  │ │
                 ─┘─┘
```

All 9 silver-layer cleaning tasks are independent of each other and
run in parallel. `build_gold` waits for all of them, builds all 5 star
schema tables, then `load_to_warehouse` pushes those tables into
Postgres, and `run_tests` validates the whole thing.

Runs inside Docker via `docker-compose.yaml` in `airflow-olist/`, which
also defines the `warehouse` (Postgres) and `metabase` services. The
Airflow container mounts the `e-commerce` project folder as a volume,
so the DAG calls the pipeline's real scripts directly rather than
duplicating any logic.

## Warehouse & dashboard

`load_to_warehouse.py` loads all 5 gold tables into a Postgres
database (`olist_gold`), making them queryable with plain SQL instead
of only via pandas/CSV. Metabase connects to this same database for
dashboarding — no separate ETL needed for the BI layer, since it reads
directly from the tables Airflow keeps up to date.

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
duplicated or dropped rows. Runs automatically as the last step of the
Airflow DAG, or manually anytime after a change to the pipeline.

## Dataset

[Olist Brazilian E-Commerce Public Dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
— real (anonymized) orders from a Brazilian e-commerce marketplace,
2016-2018.
