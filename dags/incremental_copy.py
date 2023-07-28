import time
from datetime import datetime, timedelta, date 
import os
import json

from airflow.models import DAG
from airflow.operators.python_operator import PythonOperator

import mysql.connector
from mysql.connector import MySQLConnection
from mysql.connector import cursor

from pymysqlreplication import BinLogStreamReader
from pymysqlreplication.row_event import (
    DeleteRowsEvent,
    UpdateRowsEvent,
    WriteRowsEvent
)

from airflow.providers.mysql.hooks.mysql import MySqlHook
from google.cloud import bigquery
from google.oauth2 import service_account

# Import other packages
from packages.config import CONFIG

# Set Google Cloud credentials file path
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/opt/airflow/dags/marine-fusion-394105-6f8656eedaed.json'

# Define default_args dictionary for the incremental DAG
default_args_incremental = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2023, 7, 15), 
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=1),
}

# Instantiate the incremental DAG
dag_incremental = DAG(
    'gcp_extract_and_load_incremental',
    default_args=default_args_incremental,
    description='Incremental DAG to extract data from MySQL and load it into Google BigQuery',
    schedule_interval="0 10 * * *",  # Schedule it daily at 10 AM
    catchup=False,
    tags=['load_gcp', 'incremental'],
)

class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, date):
            return obj.isoformat()
        return super().default(obj)
    
# Function to extract incremental data from MySQL using Binary Log Reader
def extract_incremental_data():
    try:
    
        # Connect to MySQL database using the Airflow MySQL Hook
        mysql_hook = MySqlHook(mysql_conn_id="mysql_conn_id")
        conn: MySQLConnection = mysql_hook.get_conn()
        cursor: cursor = conn.cursor()

        ###################################
        # Retrieve the connection details as a dictionary
        connection_details = mysql_hook.get_connection(conn_id="mysql_conn_id")

        # Access individual elements (host, port, user, passwd) from the dictionary
        host = connection_details.host
        port = connection_details.port
        user = connection_details.login
        passwd = connection_details.password

        # Initialize a list to store the modified rows
        modified_rows = []


        mysql_settings = {'host': host, 'port': port, 'user': user, 'passwd': ''}
        # Create the BinLogStreamReader
        stream = BinLogStreamReader(
            connection_settings=mysql_settings,
            server_id=100,
            only_events=[DeleteRowsEvent, WriteRowsEvent, UpdateRowsEvent],
            #blocking=True,
            #resume_stream=True,
            #log_file='mysql-bin.000001',
            #log_pos=binlog_pos,
        )

        # Read the Binary Log and identify modified rows
        for binlogevent in stream:
            for row in binlogevent.rows:
                if isinstance(binlogevent, DeleteRowsEvent):
                    modified_rows.append({key: str(value) if isinstance(value, date) else value for key, value in row["values"].items()})
                elif isinstance(binlogevent, UpdateRowsEvent):
                    modified_rows.append({key: str(value) if isinstance(value, date) else value for key, value in row["after_values"].items()})
                elif isinstance(binlogevent, WriteRowsEvent):
                    modified_rows.append({key: str(value) if isinstance(value, date) else value for key, value in row["values"].items()})


        #close stream 
        stream.close()
        cursor.close()
        conn.close()

        return modified_rows

    except Exception as e:
        print("Data extract error: " + str(e))
        return []

extract_incremental_data_task = PythonOperator(
    task_id='extract_incremental_data',
    python_callable=extract_incremental_data,
    dag=dag_incremental,
)

# Modify the GCP load task to use WRITE_APPEND to add only the changes
def gcp_load_incremental(**kwargs):
    try:
        ti = kwargs['ti']
        data = ti.xcom_pull(task_ids='extract_incremental_data')
        if not data:
            print("No data changes found.")
            return

        client = bigquery.Client()
        job_config = bigquery.job.LoadJobConfig()
        credentials = service_account.Credentials.from_service_account_file('/opt/airflow/dags/marine-fusion-394105-6f8656eedaed.json')
        project_id = CONFIG.PROJECT_ID
        dataset_ref = CONFIG.DATASET_REF
        TABLE = CONFIG.TABLE_NAME
        table_id = f"{project_id}.{dataset_ref}.{TABLE}"
        rows_imported = 0
        job_config = bigquery.job.LoadJobConfig()
        # Set write_disposition parameter as WRITE_APPEND for appending only the changes
        job_config.write_disposition = bigquery.WriteDisposition.WRITE_APPEND

        print(f"Importing {len(data)} rows to {table_id}...")
        # Proceed with the data loading using the modified data
        job = client.load_table_from_json(data, table_id, job_config=job_config)
        job.result()
        print(f"Loaded {len(data)} rows to {table_id}")
    except Exception as e:
        print("Data load error: " + str(e))

gcp_load_incremental_task = PythonOperator(
    task_id='gcp_load_incremental',
    python_callable=gcp_load_incremental,
    provide_context=True,
    dag=dag_incremental,
)

# Set task dependencies for the incremental DAG
extract_incremental_data_task >> gcp_load_incremental_task


