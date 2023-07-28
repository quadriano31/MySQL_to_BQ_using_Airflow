import time
from datetime import datetime
import os

from airflow.decorators import dag, task
from airflow.providers.mysql.hooks.mysql import MySqlHook
from google.cloud import bigquery
from google.oauth2 import service_account

# Import other packages
from packages.config import CONFIG

# Set Google Cloud credentials file path
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/opt/airflow/dags/marine-fusion-394105-6f8656eedaed.json'

# Declare Dag
@dag(schedule_interval="0 10 * * *", 
     start_date=datetime(2022, 2, 15), 
     catchup=False, tags=['load_gcp'])


def gcp_extract_and_load():
    
    # Define the SQL extract task
    @task()
    def sql_extract():
        try:
            hook = MySqlHook(mysql_conn_id="mysql_conn_id", schema='employees')
            query = f"""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'employees' AND table_name = '{CONFIG.TABLE_NAME}'
            """
            records = hook.get_records(sql=query)
            print(records)
            tbl_name = records[0]
            return tbl_name
        except Exception as e:
            print("Data extract error: " + str(e))

    # Define the GCP load task
    @task()
    def gcp_load(tbl_name: dict):
        try:
            client = bigquery.Client()
            job_config = bigquery.job.LoadJobConfig()
            credentials = service_account.Credentials.from_service_account_file('/opt/airflow/dags/marine-fusion-394105-6f8656eedaed.json')
            project_id = CONFIG.PROJECT_ID
            dataset_ref = CONFIG.DATASET_REF
            TABLE = CONFIG.TABLE_NAME
            table_id = f"{project_id}.{dataset_ref}.{TABLE}"
            rows_imported = 0
            job_config = bigquery.job.LoadJobConfig()
            # Set write_disposition parameter as WRITE_APPEND for appending to the table
            job_config.write_disposition = bigquery.WriteDisposition.WRITE_TRUNCATE

            hook = MySqlHook(mysql_conn_id="mysql_conn_id", schema='employees')

            for table_name in tbl_name:
                # print(table_name)
                query = f'SELECT * FROM {table_name}'
                df = hook.get_pandas_df(query)
                print(f'Importing rows {rows_imported} to {rows_imported + len(df)}... for table {table_name}')
                
                # Then proceed with the data loading
                job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
                job.result()  
                table = client.get_table(table_id)  # Make an API request.
                print(
                    f"Loaded {table.num_rows} rows and {len(table.schema)} columns to {table_id}"
                )
                #pandas_gbq.to_gbq(df, f'{dataset_ref}.src_{table_name}', project_id=project_id,if_exists="replace")
        except Exception as e:
            print("Data load error: " + str(e))
    
    # Call task functions
    tbl_name = sql_extract()
    tbl_summary = gcp_load(tbl_name)

# Instantiate the DAG
gcp_extract_and_load_dag = gcp_extract_and_load()
