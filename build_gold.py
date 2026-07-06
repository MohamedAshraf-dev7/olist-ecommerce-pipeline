import pandas as pd

# # ==========================================================
# # DIM_CUSTOMERS
# # One row per customer, enriched with geolocation (city/state/lat/lng)
# # joined in via zip code prefix.
# # ==========================================================

customers = pd.read_csv("silver/customers_info_clean.csv", dtype={"customer_zip_code_prefix": str})
geolocation = pd.read_csv("silver/geolocation_data_clean.csv", dtype={"geolocation_zip_code_prefix": str})

geolocation["geolocation_zip_code_prefix"] = geolocation["geolocation_zip_code_prefix"].str.zfill(5)

print("customers rows:", customers.shape[0])

dim_customers = customers.merge(
    geolocation,
    left_on="customer_zip_code_prefix",
    right_on="geolocation_zip_code_prefix",
    how="left",
)

print("dim_customers rows:", dim_customers.shape[0])

dim_customers.to_csv("gold/dim_customers.csv", index=False)
print("Saved gold/dim_customers.csv")



# # ==========================================================
# # FACT_ORDERS
# # One row per order, with item/payment/review info aggregated in.
# # ==========================================================

orders = pd.read_csv("silver/orders_info_clean.csv", parse_dates=[
    "order_purchase_timestamp", "order_approved_at",
    "order_delivered_carrier_date", "order_delivered_customer_date",
    "order_estimated_delivery_date",
])
items = pd.read_csv("silver/order_items_clean.csv")

print("orders rows:", orders.shape[0])

# Collapse order_items from many-rows-per-order to one row per order
items_agg = items.groupby("order_id", as_index=False).agg(
    nums_items=("order_item_id", "count"),
    total_price=("price", "sum"),
    total_freight=("freight_value", "sum"),
    nums_unique_products=("product_id", "nunique"),
    nums_unique_sellers=("seller_id", "nunique"),
)

fact_orders = orders.merge(items_agg, on="order_id", how="left")
print("fact_orders rows:", fact_orders.shape[0])
print("orders with no item match:", fact_orders['nums_items'].isna().sum())


payments = pd.read_csv("silver/order_payments_clean.csv")
# Some orders have multiple payment records (e.g. split between voucher
# and credit card) -- collapsing to one row per order before merging,
# same reasoning as order_items above.
payments_agg = payments.groupby("order_id", as_index=False).agg(
    total_payment_value=("payment_value", "sum"),
    payment_types=("payment_type", lambda x: ", ".join(sorted(set(x)))),
    nums_payments=("payment_sequential", "count"),
)

fact_orders = fact_orders.merge(payments_agg, on="order_id", how="left")
print("fact_orders rows after payments merge:", fact_orders.shape[0])
print("orders with no payment match:", fact_orders['total_payment_value'].isna().sum())



reviews = pd.read_csv("silver/order_reviews_clean.csv", parse_dates=["review_creation_date"])

# Some orders have multiple reviews -- keep the latest one per order
reviews_latest = (
    reviews.sort_values("review_creation_date")
    .drop_duplicates(subset="order_id", keep="last")
    [["order_id", "review_score", "has_comment"]]
)

fact_orders = fact_orders.merge(reviews_latest, on="order_id", how="left")
print("fact_orders rows after reviews merge:", fact_orders.shape[0])
print("orders with no review:", fact_orders['review_score'].isna().sum())


print(fact_orders.shape)
print(fact_orders.columns.tolist())

fact_orders.to_csv('gold/fact_orders.csv', index=False)
print("Saved gold/fact_orders.csv")


# # ==========================================================
# # DIM_PRODUCTS
# # One row per product, with English category name joined in.
# # ==========================================================
products = pd.read_csv("silver/products_info_clean.csv")
translation = pd.read_csv("silver/product_category_translation_clean.csv")

print("products rows:", products.shape[0])

dim_products = products.merge(translation, on="product_category_name", how="left")

# 610 rows are legitimately 'unknown' (no listing info at all -- expected,
# already flagged earlier). 13 rows have a real Portuguese category name
# that's simply missing from the translation table itself -- a genuine
# gap in the source data. Falling back to the Portuguese name for those,
# rather than leaving them null, so the row stays usable for grouping.
dim_products["product_category_name_english"] = dim_products["product_category_name_english"].fillna(
    dim_products["product_category_name"]
)

print("dim_products rows:", dim_products.shape[0])
print("missing english category after fallback:", dim_products["product_category_name_english"].isna().sum())

dim_products.to_csv("gold/dim_products.csv", index=False)
print("Saved gold/dim_products.csv")


# # ==========================================================
# # DIM_SELLER
# # one row per seller with just descriptive info.
# # ==========================================================
sellers = pd.read_csv("silver/sellers_info_clean.csv")

print("sellers rows:", sellers.shape[0])

dim_sellers = sellers.copy()

print("dim_sellers rows:", dim_sellers.shape[0])

dim_sellers.to_csv("gold/dim_sellers.csv", index=False)
print("Saved gold/dim_sellers.csv")

# ==========================================================
# FACT_ORDER_ITEMS
# One row per order item -- the true transaction grain, linked to
# customer, product, and seller dimensions.
# ==========================================================
items = pd.read_csv("silver/order_items_clean.csv", parse_dates=["shipping_limit_date"])
orders = pd.read_csv("silver/orders_info_clean.csv")
products = pd.read_csv("silver/products_info_clean.csv")
sellers = pd.read_csv("silver/sellers_info_clean.csv")

print("order_items rows:", items.shape[0])

# Bring in customer_id via orders (every order_item belongs to exactly
# one order, so this is a clean many-to-one join, no row growth expected)
fact_order_items = items.merge(orders[["order_id", "customer_id"]], on="order_id", how="left")
print("after customer join:", fact_order_items.shape[0],
    "| missing customer:", fact_order_items["customer_id"].isna().sum())

# 4 product_ids (8 order_item rows) exist in order_items but not in the
# cleaned products table -- they were dropped during products cleaning
# for having invalid (<= 0) physical dimensions. Keeping these rows here
# regardless: they represent real sales/revenue, and dropping them would
# silently understate revenue just because a dimension attribute was bad.
# Their product_key will simply be null (product details unknown, sale still real).
fact_order_items = fact_order_items.merge(
    products[["product_id", "product_category_name"]], on="product_id", how="left"
)
print("after product join:", fact_order_items.shape[0],
        "| missing product match:", fact_order_items["product_category_name"].isna().sum())

fact_order_items = fact_order_items.merge(
    sellers[["seller_id", "seller_city", "seller_state"]], on="seller_id", how="left"
)
print("after seller join:", fact_order_items.shape[0],
        "| missing seller match:", fact_order_items["seller_city"].isna().sum())

# Final integrity check: row count must match the original order_items table
print("final row count matches order_items:", fact_order_items.shape[0] == items.shape[0])

fact_order_items.to_csv("gold/fact_order_items.csv", index=False)
print("Saved gold/fact_order_items.csv")
