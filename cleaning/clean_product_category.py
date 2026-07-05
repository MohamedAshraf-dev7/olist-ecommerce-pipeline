import pandas as pd 


df = pd.read_csv('bronze/product_category_name.csv')

print(df.shape)
print(df.head())
print(df.info())
print(df.isna().sum())
print(df.duplicated().sum()) 

# both numbers equal 71, every category has exactly one unique translation — a clean 1-to-1 map
print(df['product_category_name'].nunique())
print(df['product_category_name_english'].nunique())

df.to_csv('silver/product_category_translation_clean.csv', index=False)
print("Saved silver/product_category_translation_clean.csv")