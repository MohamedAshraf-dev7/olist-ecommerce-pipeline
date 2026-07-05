import pandas as pd

df = pd.read_csv("bronze/orders_info.csv")

print(df.shape)
print(df.head())
print(df.info())
print(df.isna().sum())
print(df.duplicated().sum())

df['order_purchase_timestamp'] = pd.to_datetime(df['order_purchase_timestamp'], errors='coerce')
df['order_approved_at'] = pd.to_datetime(df['order_approved_at'], errors='coerce')
df['order_delivered_carrier_date'] = pd.to_datetime(df['order_delivered_carrier_date'], errors='coerce')
df['order_delivered_customer_date'] = pd.to_datetime(df['order_delivered_customer_date'], errors='coerce')
df['order_estimated_delivery_date'] = pd.to_datetime(df['order_estimated_delivery_date'], errors='coerce')

# Clean status text before using it in any logic below
df['order_status'] = df['order_status'].str.strip().str.lower()

# Nulls in date columns are expected for non-delivered statuses (e.g. a
# canceled order never gets approved/shipped). But a 'delivered' order
# missing any of these dates is a genuine inconsistency -- flagging
# rather than dropping, since these are still real orders/customers.
df['status_date_inconsistent'] = (
    (df['order_status'] == 'delivered') &
    (df['order_approved_at'].isna() |
    df['order_delivered_carrier_date'].isna() |
    df['order_delivered_customer_date'].isna())
)
print("delivered orders with missing dates:", df['status_date_inconsistent'].sum())

# Sanity check: dates should never be earlier than the purchase date
bad_delivery = df['order_delivered_customer_date'] < df['order_purchase_timestamp']
bad_approval = df['order_approved_at'] < df['order_purchase_timestamp']
print("impossible delivery dates:", bad_delivery.sum())
print("impossible approval dates:", bad_approval.sum())

df.to_csv('silver/orders_info_clean.csv', index=False)
print("Saved silver/orders_info_clean.csv")