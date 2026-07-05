import pandas as pd 


df = pd.read_csv('bronze/products_info.csv')


print(df.shape)
print(df.head())    
print(df.info())
print(df.isna().sum())
print(df.duplicated().sum())

df.rename(columns={
    'product_name_lenght':'product_name_length',
    'product_description_lenght':'product_description_length'
}, inplace=True)

# 1,603 order_items reference these products -- dropping them would orphan
# real transactions when merging later. Flag instead, and fill category
# with a placeholder so the row stays joinable and identifiable downstream.
df['missing_listing_info'] = df['product_category_name'].isna()
df['product_category_name'] = df['product_category_name'].fillna('unknown')

# Fill missing numeric values with the median of each column
numeric_cols = ['product_weight_g','product_length_cm','product_height_cm','product_width_cm']
for col in numeric_cols:
    df[col] = df[col].fillna(df[col].median())

# Remove rows with physically invalid dimensions (zero or negative)
df = df[(df['product_weight_g'] > 0) &
        (df['product_length_cm'] > 0) &
        (df['product_height_cm'] > 0) &
        (df['product_width_cm'] > 0)]


df.to_csv('silver/products_info_clean.csv', index=False)
print("Saved silver/products_info_clean.csv")