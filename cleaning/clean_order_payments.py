import pandas as pd

df = pd.read_csv("bronze/order_payments.csv")

print(df.shape)
print(df.head())
print(df.info())
print(df.isna().sum())
print(df.duplicated().sum())

# 'not_defined' is a known placeholder in this dataset -- not a real
# payment method. All 3 occurrences are the order's *only* payment record,
# with payment_value == 0 (likely a failed/uncompleted transaction).
# Relabeled as an explicit 'unknown' category rather than dropped, so
# these orders don't silently disappear from payment-based joins/aggregations.
print("not_defined rows:", (df['payment_type'] == 'not_defined').sum())
df['payment_type'] = df['payment_type'].replace('not_defined', 'unknown')

# Sanity check: payment_value should never be negative
print("negative payment_value rows:", (df['payment_value'] < 0).sum())

# payment_installments == 0 is logically impossible for a completed
# payment (a real payment happens in at least 1 installment). Found 2
# rows with real, nonzero payment_value but 0 installments -- treating
# as a data-entry default and flagging before correcting to 1, so the
# fix stays visible/auditable rather than silently overwritten.
print("payment_installments == 0 rows:", (df['payment_installments'] == 0).sum())
df['installments_corrected'] = df['payment_installments'] == 0
df.loc[df['payment_installments'] == 0, 'payment_installments'] = 1

# payment_sequential is a position counter within an order (1st payment,
# 2nd payment, etc. -- e.g. paying partly by voucher, partly by credit
# card), NOT a unique row ID on its own. The true unique key for this
# table is the combination of order_id + payment_sequential.
print("duplicate (order_id, payment_sequential) pairs:",
    df.duplicated(subset=['order_id', 'payment_sequential']).sum())

df.to_csv('silver/order_payments_clean.csv', index=False)
print("Saved silver/order_payments_clean.csv")