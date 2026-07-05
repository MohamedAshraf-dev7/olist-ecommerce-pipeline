import pandas as pd
import unicodedata

df = pd.read_csv('bronze/sellers_info.csv')


print(df.shape)
print(df.head())
print(df.info())
print(df.isna().sum())
print(df.duplicated().sum())

# zip prefix stored as int silently drops leading zeros (e.g. 01310 -> 1310)
df['seller_zip_code_prefix'] = df['seller_zip_code_prefix'].astype(str).str.zfill(5)

# zip_code_prefix is stored as int, which silently drops leading zeros
# (e.g. 01310 -> 1310). zfill(5) restores the correct 5-digit format.
def remove_accents(text):
    if pd.isna(text):
        return text
    normalized = unicodedata.normalize('NFKD', text)
    return ''.join(c for c in normalized if not unicodedata.combining(c))
df['seller_city'] = df['seller_city'].str.strip().str.lower().apply(remove_accents)


# 'sp' and 'sbc' are known abbreviations for Sao Paulo / Sao Bernardo do
# Campo. Verified all rows with these values show seller_state == 'SP'
# before applying, to avoid mis-mapping an unrelated city.
city_fixes = {
    'sp': 'sao paulo',
    'sbc': 'sao bernardo do campo',
}
df['seller_city'] = df['seller_city'].replace(city_fixes)

df.to_csv('silver/sellers_info_clean.csv', index=False)
print("Saved silver/sellers_info_clean.csv")
