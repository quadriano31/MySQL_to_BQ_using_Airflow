-- models/employee_transform.sql

-- Declare the dbt model
{{ config(
    materialized='view',
    unique_key='emp_no'
) }}

-- Write the SQL code within the dbt model
SELECT
    emp_no,
    birth_date,
    first_name,
    last_name,
    CASE 
        WHEN gender = 'M' THEN 'Male'
        WHEN gender = 'F' THEN 'Female'
        ELSE gender
    END AS gender,
    hire_date
FROM
    `employees_db`.employees
