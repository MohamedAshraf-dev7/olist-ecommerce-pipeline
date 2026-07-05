import pandas as pd 

df = pd.read_csv("bronze/order_reviews.csv")

print(df.shape)
print(df.head())
print(df.info())
print(df.isna().sum())
print(df.duplicated().sum())

df['review_creation_date'] = pd.to_datetime(df['review_creation_date'], errors='coerce')
df['review_answer_timestamp'] = pd.to_datetime(df['review_answer_timestamp'], errors='coerce')

df['review_comment_title'] = df['review_comment_title'].fillna('')
df['review_comment_message'] = df['review_comment_message'].fillna('')

# review_id should be unique -- 814 rows share a duplicate review_id.
# Keeping the most recent copy (latest review_creation_date), assuming
# it's the corrected/final version.
df = df.sort_values('review_creation_date').drop_duplicates(subset='review_id', keep='last')
print("duplicate review_ids after fix:", df.duplicated(subset='review_id').sum())

df['order_has_multiple_reviews'] = df.duplicated(subset='order_id', keep=False)
# Flag whether a written comment exists BEFORE filling nulls, otherwise
# an empty string and "never had a comment" become indistinguishable
df['has_comment'] = df['review_comment_message'].notna()


df.to_csv('silver/order_reviews_clean.csv', index=False)
print("Saved silver/order_reviews_clean.csv")
