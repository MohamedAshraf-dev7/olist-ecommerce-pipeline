import pandas as pd
import unicodedata

df = pd.read_csv('bronze/geolocation_data.csv')

print(df.shape)
print(df.head())
print(df.info())
print(df.isna().sum())
print(df.duplicated().sum())

df = df.drop_duplicates()

# City names have inconsistent accents (e.g. "São Paulo" vs "Sao Paulo"),
# which fragments groupby/join results. NFKD normalization splits each
# accented char into base letter + accent mark, then we drop the marks.
def remove_accents(text):
    if pd.isna(text):
        return text
    normalized = unicodedata.normalize('NFKD', text)
    return ''.join(c for c in normalized if not unicodedata.combining(c))

df['geolocation_city'] = df['geolocation_city'].str.strip().str.lower().apply(remove_accents)

# Accent-stripping doesn't catch typos, abbreviations, or corrupted encoding
# (e.g. 'sp'/'rj'/'bh' as shorthand, 'sa£o paulo' from a bad encoding
# conversion). These are rare enough to fix by hand rather than programmatically.
city_fixes = {
    'saopaulo': 'sao paulo',
    'sp': 'sao paulo',
    'sa£o paulo': 'sao paulo',
    'rj': 'rio de janeiro',
    'bh': 'belo horizonte',
}
df['geolocation_city'] = df['geolocation_city'].replace(city_fixes)

# Found via cross-checking city against state: 2 rows tagged city =
# "rio de janeiro" but state = "AC" (Acre). Verified via lat/lng and zip
# code (both match Rio de Janeiro, not Acre) -- state was the actual
# error here, not the city. Fixing only these 2 confirmed rows.
df.loc[
    (df['geolocation_city'] == 'rio de janeiro') & (df['geolocation_state'] == 'AC'),
    'geolocation_state'
] = 'RJ'

# 9,054 rows had lat/lng outside Brazil's real bounding box (e.g. Portugal,
# Argentina, Philippines coordinates) -- likely bad source data with no way
# to recover the correct value, so dropping rather than guessing a fix.
df = df[
    df['geolocation_lat'].between(-34, 5) &
    df['geolocation_lng'].between(-74, -35)
]

# Raw file has ~1 row per GPS ping (many per zip code). Collapsing to one
# row per zip prefix makes this joinable 1:1 with customers/sellers, which
# only have a zip prefix, not exact coordinates. Only ~2.8% of zips have
# more than one city name attached, so taking 'first' is a safe simplification.
df_zip = (
    df.groupby('geolocation_zip_code_prefix', as_index=False)
    .agg(
        geolocation_lat=('geolocation_lat', 'mean'),
        geolocation_lng=('geolocation_lng', 'mean'),
        geolocation_city=('geolocation_city', 'first'),
        geolocation_state=('geolocation_state', 'first'),
    )
)

df_zip.to_csv('silver/geolocation_data_clean.csv', index=False)
print("Saved silver/geolocation_data_clean.csv")


