"""
analyze_gold.py
================
A few real questions answered from the gold layer, to prove the star
schema is actually useful for analysis, not just a cleaning exercise.

Produces 3 PNG charts in analysis/:
  1. Top 10 product categories by revenue      (needs fact_order_items + dim_products)
  2. Monthly revenue trend                      (needs fact_orders)
  3. Review score vs. average delivery time     (needs fact_orders)

Run: python analyze_gold.py
"""

import pandas as pd
import matplotlib.pyplot as plt
import os

os.makedirs("analysis", exist_ok=True)

plt.rcParams["figure.facecolor"] = "white"
plt.rcParams["axes.facecolor"] = "white"

# ==========================================================
# 1. Top 10 product categories by revenue
# ==========================================================
items = pd.read_csv("gold/fact_order_items.csv")
products = pd.read_csv("gold/dim_products.csv")

items_with_category = items.merge(
    products[["product_id", "product_category_name_english"]], on="product_id", how="left"
)

top_categories = (
    items_with_category.groupby("product_category_name_english")["price"]
    .sum()
    .sort_values(ascending=False)
    .head(10)
)

print("Top 10 categories by revenue:")
print(top_categories)

fig, ax = plt.subplots(figsize=(9, 6))
top_categories.sort_values().plot(kind="barh", ax=ax, color="#5b8ac9")
ax.set_xlabel("Total revenue (BRL)")
ax.set_ylabel("")
ax.set_title("Top 10 Product Categories by Revenue")
plt.tight_layout()
plt.savefig("analysis/top_categories_by_revenue.png", dpi=150)
plt.close()
print("Saved analysis/top_categories_by_revenue.png\n")

# ==========================================================
# 2. Monthly revenue trend
# ==========================================================
orders = pd.read_csv("gold/fact_orders.csv", parse_dates=["order_purchase_timestamp"])

# Exclude the first and last partial months (Sep 2016 and Sep/Oct 2018
# have only a handful of orders -- not real business volume, just
# dataset edge effects that would distort the trend line)
orders["month"] = orders["order_purchase_timestamp"].dt.to_period("M")
monthly_revenue = orders.groupby("month")["total_price"].sum()
monthly_revenue = monthly_revenue.iloc[1:-2]  # trim partial edge months

print("Monthly revenue (trimmed):")
print(monthly_revenue)

fig, ax = plt.subplots(figsize=(10, 5))
monthly_revenue.plot(ax=ax, color="#5b8ac9", marker="o", markersize=3)
ax.set_xlabel("Month")
ax.set_ylabel("Total revenue (BRL)")
ax.set_title("Monthly Revenue Trend")
plt.tight_layout()
plt.savefig("analysis/monthly_revenue_trend.png", dpi=150)
plt.close()
print("Saved analysis/monthly_revenue_trend.png\n")

# ==========================================================
# 3. Review score vs. average delivery time
# ==========================================================
orders["order_delivered_customer_date"] = pd.to_datetime(orders["order_delivered_customer_date"])
orders["delivery_days"] = (
    orders["order_delivered_customer_date"] - orders["order_purchase_timestamp"]
).dt.days

# Only delivered orders with both a valid score and a valid delivery date
delivered = orders.dropna(subset=["review_score", "delivery_days"])
delivery_by_score = delivered.groupby("review_score")["delivery_days"].mean()

print("Average delivery days by review score:")
print(delivery_by_score)

fig, ax = plt.subplots(figsize=(7, 5))
delivery_by_score.plot(kind="bar", ax=ax, color="#5b8ac9")
ax.set_xlabel("Review score (1-5 stars)")
ax.set_ylabel("Average delivery time (days)")
ax.set_title("Delivery Time vs. Review Score")
ax.tick_params(axis="x", rotation=0)
plt.tight_layout()
plt.savefig("analysis/review_score_vs_delivery_time.png", dpi=150)
plt.close()
print("Saved analysis/review_score_vs_delivery_time.png")