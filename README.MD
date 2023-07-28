# MYSQL TO BIGQUERY FULL & INCREMENTAL LOAD (USING BIN LOG REPLICATION) ON AIRFLOW & DBT

This code allows you to perform full or incremental load to BigQuery from MySQL Using AIRFLOW and Transformation on DBT


## Folder structure

Airflow image --
    ---Dockerfile
    ---requirements.txt
dags
    ----dbt 
    ----packages
    ----dags script
    ----service_account.json
log---
    ---mysql
logs---
    ---airflow logs 
mysql_data----
plugins
.env
docker-compose.yaml
my.cnf
README.MD

## PREREQUISITE 

Docker & DOcker compose 

Clone the repo and run docker compose up, Ensure that all containers are healthy

## Loading the data to MySQL Server 

To Download the Employee DB and load to MySQL
```bash 
    run docker container exec -it mysql-container-id /bin/bash 
    bash curl -LOk https://github.com/datacharmer/test_db/archive/refs/heads/master.zip
    yum install unzip 
    cd test_db-master/
    mysql -t < employees.sql

```

airflow tasks test extract_and_load sql_extract 2023-07-26

airflow tasks test gcp_extract_and_load_incremental sql_extract 2023-07-26
## TO ENABLE BIN LOG REPLICATION ON MYSQL 

Create a .cnf file and map it to MySQL 

```bash
[mysqld]
server-id		 = 1
log_bin			 = /var/log/mysql/mysql-bin.log
expire_logs_days = 10
max_binlog_size  = 100M
binlog-format    = row #Very important if you want to receive write, update and delete row events
```

Enter the container 

```bash
    run docker container exec -it mysql-container-id /bin/bash
    enter the container and RUN chmod 644 /etc/mysql/conf.d/my.cnf


```
## TO confirm if BINARY LOG REPLICATION IS ON 
```bash 
    mysql -uroot
    RUN set @@global.show_compatibility_56=ON;
    RUN 
    select variable_value as "BINARY LOGGING STATUS (log_bin) :: " 
    from information_schema.global_variables where variable_name='log_bin';
```

### CREATE A GCP PROJECT 

Create a GCP project, BigQuery Dataset and Table 
Modify the CONFIG.py file and add the new details created accordingly 
Create BigQuery Dataset [click here](https://cloud.google.com/bigquery/docs/datasets)



### Permisions to give service account 
Bigquery Admin
or 
BigQuery Connection admin
Bigquery Connection user
BigQuery user

### Contributing
Contributions are welcome! If you find any issues or have suggestions for improvements, please create a GitHub issue or submit a pull request.

### License
This project is licensed under the MIT License.