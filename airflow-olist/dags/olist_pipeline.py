from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime

PROJECT_DIR = "/opt/olist_project"

default_args = {
    "owner": "olist_pipeline",
    "retries": 1,
}

with DAG(
    dag_id="olist_medallion_pipeline",
    default_args=default_args,
    description="Bronze -> Silver -> Gold pipeline for the Olist dataset",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["olist", "medallion"],
) as dag:

    # ---- Silver layer: clean each raw table ----
    clean_customers = BashOperator(
        task_id="clean_customers",
        bash_command=f"cd {PROJECT_DIR} && python cleaning/clean_customers_info.py",
    )
    clean_geolocation = BashOperator(
        task_id="clean_geolocation",
        bash_command=f"cd {PROJECT_DIR} && python cleaning/clean_geolocation.py",
    )
    clean_sellers = BashOperator(
        task_id="clean_sellers",
        bash_command=f"cd {PROJECT_DIR} && python cleaning/clean_sellers_info.py",
    )
    clean_product_category = BashOperator(
        task_id="clean_product_category",
        bash_command=f"cd {PROJECT_DIR} && python cleaning/clean_product_category.py",
    )
    clean_order_items = BashOperator(
        task_id="clean_order_items",
        bash_command=f"cd {PROJECT_DIR} && python cleaning/clean_order_items.py",
    )
    clean_products = BashOperator(
        task_id="clean_products",
        bash_command=f"cd {PROJECT_DIR} && python cleaning/clean_product_info.py",
    )
    clean_orders = BashOperator(
        task_id="clean_orders",
        bash_command=f"cd {PROJECT_DIR} && python cleaning/clean_orders_info.py",
    )
    clean_payments = BashOperator(
        task_id="clean_payments",
        bash_command=f"cd {PROJECT_DIR} && python cleaning/clean_order_payments.py",
    )
    clean_reviews = BashOperator(
        task_id="clean_reviews",
        bash_command=f"cd {PROJECT_DIR} && python cleaning/clean_order_reviews.py",
    )

    # ---- Gold layer ----
    build_gold = BashOperator(
        task_id="build_gold",
        bash_command=f"cd {PROJECT_DIR} && python build_gold.py",
    )

    # ---- Validation ----
    run_tests = BashOperator(
        task_id="run_tests",
        bash_command=f"cd {PROJECT_DIR} && python test_cleaning.py",
    )
    
    load_to_warehouse = BashOperator(
    task_id="load_to_warehouse",
    bash_command=f"cd {PROJECT_DIR} && python load_to_warehouse.py",
    env={"POSTGRES_HOST": "warehouse"},
)

    # ---- Dependencies ----
    silver_tasks = [
        clean_customers, clean_geolocation, clean_sellers,
        clean_product_category, clean_order_items, clean_products,
        clean_orders, clean_payments, clean_reviews,
    ]

    build_gold >> load_to_warehouse >> run_tests