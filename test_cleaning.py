"""
test_cleaning.py
=================
Validation checks for the 9 cleaned Olist tables. Run this after the
cleaning scripts to prove each known data issue was actually handled.

Each check prints PASS or FAIL. Doesn't stop on the first failure --
runs everything so you get a full report in one pass.

Run: python test_cleaning.py
"""

import pandas as pd

CLEAN_DIR = "silver"
GOLD_DIR = "gold"
results = []


def check(description, condition):
    status = "PASS" if condition else "FAIL"
    results.append((status, description))
    print(f"[{status}] {description}")


# =================================================================
# CUSTOMERS
# =================================================================
df = pd.read_csv(f"{CLEAN_DIR}/customers_info_clean.csv", dtype={"customer_zip_code_prefix": str})

check("customers: no missing values", df.isna().sum().sum() == 0)
check("customers: no exact duplicate rows", df.duplicated().sum() == 0)
check("customers: is_repeat_customer flag exists", "is_repeat_customer" in df.columns)
check(
    "customers: all zip codes are exactly 5 digits",
    (df["customer_zip_code_prefix"].astype(str).str.len() == 5).all(),
)
check(
    "customers: customer_id is fully unique (one row per order)",
    df["customer_id"].is_unique,
)

# =================================================================
# GEOLOCATION
# =================================================================
df = pd.read_csv(f"{CLEAN_DIR}/geolocation_data_clean.csv")

check("geolocation: no missing values", df.isna().sum().sum() == 0)
check(
    "geolocation: one row per zip code prefix (aggregated)",
    df["geolocation_zip_code_prefix"].is_unique,
)
check(
    "geolocation: latitude within Brazil's bounds",
    df["geolocation_lat"].between(-34, 5).all(),
)
check(
    "geolocation: longitude within Brazil's bounds",
    df["geolocation_lng"].between(-74, -35).all(),
)
check(
    "geolocation: no leftover known bad city labels (sp/rj/bh/saopaulo)",
    not df["geolocation_city"].isin(["sp", "rj", "bh", "saopaulo"]).any(),
)
check(
    "geolocation: no rio de janeiro city rows mislabeled with wrong state",
    not ((df["geolocation_city"] == "rio de janeiro") & (df["geolocation_state"] == "AC")).any(),
)

# =================================================================
# SELLERS
# =================================================================
df = pd.read_csv(f"{CLEAN_DIR}/sellers_info_clean.csv", dtype={"seller_zip_code_prefix": str})

check("sellers: no missing values", df.isna().sum().sum() == 0)
check("sellers: no exact duplicate rows", df.duplicated().sum() == 0)
check(
    "sellers: all zip codes are exactly 5 digits",
    (df["seller_zip_code_prefix"].astype(str).str.len() == 5).all(),
)
check("sellers: seller_id is fully unique", df["seller_id"].is_unique)
check(
    "sellers: no leftover abbreviated city labels (sp/sbc)",
    not df["seller_city"].isin(["sp", "sbc"]).any(),
)

# =================================================================
# PRODUCT CATEGORY TRANSLATION
# =================================================================
df = pd.read_csv(f"{CLEAN_DIR}/product_category_translation_clean.csv")

check("product_category_translation: no missing values", df.isna().sum().sum() == 0)
check(
    "product_category_translation: 1-to-1 mapping (no duplicate category names)",
    df["product_category_name"].is_unique,
)

# =================================================================
# ORDER ITEMS
# =================================================================
df = pd.read_csv(f"{CLEAN_DIR}/order_items_clean.csv", parse_dates=["shipping_limit_date"])

check("order_items: no missing values", df.isna().sum().sum() == 0)
check(
    "order_items: shipping_limit_date parsed as real datetime",
    str(df["shipping_limit_date"].dtype).startswith("datetime"),
)
check("order_items: no zero or negative prices", (df["price"] > 0).all())
check("order_items: no negative freight values", (df["freight_value"] >= 0).all())
check(
    "order_items: (order_id, order_item_id) is a unique combination",
    not df.duplicated(subset=["order_id", "order_item_id"]).any(),
)

# =================================================================
# PRODUCTS
# =================================================================
df = pd.read_csv(f"{CLEAN_DIR}/products_info_clean.csv")

check("products: typo columns renamed (no '_lenght' columns remain)", 
      not any("lenght" in c for c in df.columns))
check("products: missing_listing_info flag exists", "missing_listing_info" in df.columns)
check(
    "products: product_category_name has no nulls (filled with 'unknown')",
    df["product_category_name"].isna().sum() == 0,
)
check(
    "products: no zero/negative physical dimensions remain",
    (df[["product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm"]] > 0).all().all(),
)
check("products: product_id is fully unique", df["product_id"].is_unique)

# =================================================================
# ORDERS
# =================================================================
df = pd.read_csv(
    f"{CLEAN_DIR}/orders_info_clean.csv",
    parse_dates=[
        "order_purchase_timestamp", "order_approved_at",
        "order_delivered_carrier_date", "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ],
)

check("orders: order_id is fully unique", df["order_id"].is_unique)
check(
    "orders: order_status is clean (lowercase, no whitespace)",
    (df["order_status"] == df["order_status"].str.strip().str.lower()).all(),
)
check("orders: status_date_inconsistent flag exists", "status_date_inconsistent" in df.columns)
check(
    "orders: no delivery date earlier than purchase date",
    not (df["order_delivered_customer_date"] < df["order_purchase_timestamp"]).any(),
)
check(
    "orders: no approval date earlier than purchase date",
    not (df["order_approved_at"] < df["order_purchase_timestamp"]).any(),
)

# =================================================================
# PAYMENTS
# =================================================================
df = pd.read_csv(f"{CLEAN_DIR}/order_payments_clean.csv")

check("payments: no missing values", df.isna().sum().sum() == 0)
check(
    "payments: no 'not_defined' payment_type remains",
    not (df["payment_type"] == "not_defined").any(),
)
check("payments: no negative payment_value", (df["payment_value"] >= 0).all())
check(
    "payments: no zero-installment rows remain",
    not (df["payment_installments"] == 0).any(),
)
check("payments: installments_corrected flag exists", "installments_corrected" in df.columns)
check(
    "payments: (order_id, payment_sequential) is a unique combination",
    not df.duplicated(subset=["order_id", "payment_sequential"]).any(),
)

# =================================================================
# REVIEWS
# =================================================================
df = pd.read_csv(
    f"{CLEAN_DIR}/order_reviews_clean.csv",
    parse_dates=["review_creation_date", "review_answer_timestamp"],
    keep_default_na=False,
    na_values=[],
)
# keep_default_na=False stops pandas from re-reading the empty strings we
# saved (from filled comment fields) back in as NaN -- without this, the
# CSV round-trip silently undoes the fillna('') we already did.

check("reviews: review_id is fully unique (duplicates removed)", df["review_id"].is_unique)
check("reviews: has_comment flag exists", "has_comment" in df.columns)
check(
    "reviews: no nulls remain in comment columns (filled with '')",
    df["review_comment_title"].isna().sum() == 0 and df["review_comment_message"].isna().sum() == 0,
)
check("reviews: all review_score values within 1-5", df["review_score"].between(1, 5).all())
check(
    "reviews: no answer timestamp earlier than creation date",
    not (df["review_answer_timestamp"] < df["review_creation_date"]).any(),
)
check("reviews: order_has_multiple_reviews flag exists", "order_has_multiple_reviews" in df.columns)

# =================================================================
# GOLD LAYER: dim_customers + fact_orders
# =================================================================
dim_customers = pd.read_csv(f"{GOLD_DIR}/dim_customers.csv", dtype={"customer_zip_code_prefix": str})
orders_raw = pd.read_csv(f"{CLEAN_DIR}/order_items_clean.csv")
fact_orders = pd.read_csv(f"{GOLD_DIR}/fact_orders.csv")

check(
    "dim_customers: customer_id is fully unique",
    dim_customers["customer_id"].is_unique,
)
check(
    "fact_orders: order_id is fully unique (no merge duplicated rows)",
    fact_orders["order_id"].is_unique,
)
check(
    "fact_orders: row count matches original orders table exactly",
    fact_orders.shape[0] == orders_raw.shape[0],
)
check(
    "fact_orders: every customer_id exists in dim_customers (referential integrity)",
    fact_orders["customer_id"].isin(dim_customers["customer_id"]).all(),
)
check(
    "fact_orders: no negative total_price",
    (fact_orders["total_price"].dropna() >= 0).all(),
)
check(
    "fact_orders: no negative total_freight",
    (fact_orders["total_freight"].dropna() >= 0).all(),
)
check(
    "fact_orders: no negative total_payment_value",
    (fact_orders["total_payment_value"].dropna() >= 0).all(),
)

# =================================================================
# GOLD LAYER (extended): dim_products, dim_sellers, fact_order_items
# =================================================================
dim_products = pd.read_csv(f"{GOLD_DIR}/dim_products.csv")
dim_sellers = pd.read_csv(f"{GOLD_DIR}/dim_sellers.csv")
order_items_raw = pd.read_csv(f"{CLEAN_DIR}/order_items_clean.csv")
fact_order_items = pd.read_csv(f"{GOLD_DIR}/fact_order_items.csv")

check(
    "dim_products: product_id is fully unique",
    dim_products["product_id"].is_unique,
)
check(
    "dim_products: product_category_name_english has no nulls (fallback applied)",
    dim_products["product_category_name_english"].isna().sum() == 0,
)
check(
    "dim_sellers: seller_id is fully unique",
    dim_sellers["seller_id"].is_unique,
)
check(
    "fact_order_items: row count matches original order_items table exactly",
    fact_order_items.shape[0] == order_items_raw.shape[0],
)
check(
    "fact_order_items: every customer_id exists in dim_customers",
    fact_order_items["customer_id"].isin(dim_customers["customer_id"]).all(),
)
check(
    "fact_order_items: every seller_id exists in dim_sellers",
    fact_order_items["seller_id"].isin(dim_sellers["seller_id"]).all(),
)
check(
    "fact_order_items: no zero/negative prices",
    (fact_order_items["price"] > 0).all(),
)
check(
    "fact_order_items: no negative freight values",
    (fact_order_items["freight_value"] >= 0).all(),
)

# =================================================================
# SUMMARY
# =================================================================
passed = sum(1 for status, _ in results if status == "PASS")
failed = sum(1 for status, _ in results if status == "FAIL")
print(f"\n{'='*50}")
print(f"TOTAL: {passed} passed, {failed} failed, {len(results)} checks run")
if failed:
    print("\nFailed checks:")
    for status, desc in results:
        if status == "FAIL":
            print(f"  - {desc}")