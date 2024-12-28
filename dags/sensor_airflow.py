import airflow
from airflow import DAG
from airflow.operators.python import PythonOperator

import random
import time
import json
from datetime import datetime
from kafka import KafkaProducer
import logging


# Function to simulate sensor data
def generate_sensor_data(id):
    sensor_data = {
        "sensor_id": id,
        "temperature": round(random.uniform(29.0, 30.0), 2),  # Random temperature between 20.0 and 30.0 degrees
        "humidity": round(random.uniform(50.0, 51.0), 2),     # Random humidity between 30.0% and 60.0%
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    return sensor_data

def stream_data():
    producer = KafkaProducer(bootstrap_servers=['localhost:9092'], max_block_ms=5000)
    curr_time = time.time()
    id = 0
    while True:
        if time.time() > curr_time + 60: #1 minute
            break
        try:
            id += 1
            res = generate_sensor_data(id)
            if id >= 5:
                id = 0
            print(res, end="\r")
            producer.send('sensor_data', json.dumps(res).encode('utf-8'))
            time.sleep(1)
        except Exception as e:
            logging.error(f'An error occured: {e}')
            continue


    
dag = DAG(
    dag_id = "sensor_data",
    default_args = {
        "owner" : "Prabakar Sundar",
        "start_date" : airflow.utils.dates.days_ago(1),
    },
    schedule_interval = "*/5 * * * *",
    catchup = False
)

start = PythonOperator(
    task_id = "start",
    python_callable = lambda: print("Jobs Started"),
    dag=dag
)

python_job = PythonOperator(
    task_id="sensor_data_generator",
    python_callable=stream_data,
    dag=dag
)

end = PythonOperator(
    task_id="end",
    python_callable = lambda: print("Jobs completed successfully"),
    dag=dag
)

start >> python_job >> end