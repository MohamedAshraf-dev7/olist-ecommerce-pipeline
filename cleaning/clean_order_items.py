import pandas as pd  


df = pd.read_csv('bronze/order_items.csv')



print(df.shape)
print(df.head())        
print(df.info())
print(df.isna().sum())
print(df.duplicated().sum()) 

# shipping_limit_date was loaded as plain text; converting to real
# datetime so date comparisons/filters work correctly later
df['shipping_limit_date'] = pd.to_datetime(df['shipping_limit_date'], errors='coerce')


# Verified no invalid prices/freight before saving
print("rows with price <= 0:", (df['price'] <= 0).sum())
print("rows with negative freight:", (df['freight_value'] < 0).sum())

df.to_csv('silver/order_items_clean.csv', index=False)
print("Saved silver/order_items_clean.csv")