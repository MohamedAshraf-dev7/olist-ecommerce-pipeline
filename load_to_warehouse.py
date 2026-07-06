import os
import pandas as pd
from sqlalchemy import create_engine

# Defaults to 'localhost' when you run this yourself; Airflow will
# override this to 'warehouse' (the Docker Compose service name) since
# 'localhost' means something different from inside a container.
DB_HOST = os.environ.get("POSTGRES_HOST", "localhost")

DB_USER = "analytics"
DB_PASSWORD = "analytics"
DB_NAME = "olist_gold"
DB_PORT = 5432

engine = create_engine(
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

tables = ["dim_customers", "dim_products", "dim_sellers", "fact_orders", "fact_order_items"]

for table in tables:
    df = pd.read_csv(f"gold/{table}.csv")
    df.to_sql(table, engine, if_exists="replace", index=False)
    print(f"Loaded {table}: {len(df)} rows")

print("All gold tables loaded into Postgres.")