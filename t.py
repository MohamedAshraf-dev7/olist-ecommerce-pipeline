
import pandas as pd

df = pd.read_csv("gold/fact_order_items.csv")
print(df.groupby("product_category_name")["seller_city"].count().sort_values(ascending=False).head(10))

