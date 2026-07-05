import pandas as pd 

df = pd.read_csv("bronze/customers_info.csv")

print(df.shape)
print(df.head())
print(df.info())
print(df.isna().sum())
print(df.duplicated().sum())

# customer_unique_id has fewer unique values than customer_id — meaning
# some people placed multiple orders. This is expected, NOT a duplicate
# to drop. Flagging instead of dropping preserves order history.
df["is_repeat_customer"] = df.duplicated(subset="customer_unique_id", keep=False)

print(df["customer_id"].nunique())
print(df["customer_unique_id"].nunique())
print(df["customer_city"].str.islower().all())
print(df["customer_state"].unique())

# zip_code_prefix is stored as int, which silently drops leading zeros
# (e.g. 01310 -> 1310). zfill(5) restores the correct 5-digit format.
df["customer_zip_code_prefix"] = df["customer_zip_code_prefix"].astype(str).str.zfill(5)
print(df["customer_zip_code_prefix"].str.len().value_counts())

df.to_csv("silver/customers_info_clean.csv", index=False)
print("Saved silver/customers_info_clean.csv")
    