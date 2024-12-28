import airflow
from airflow import DAG
from airflow.operators.python import PythonOperator
import json
from datetime import datetime

from kafka import KafkaConsumer
from elasticsearch import Elasticsearch

def index_to_elasticsearch(es, sensor_data):
    try:
        # Convert timestamp string to ISO 8601 format
        timestamp_str = sensor_data['timestamp']
        timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        iso_timestamp = timestamp.isoformat() + 'Z'  # Add 'Z' to indicate UTC

        # Index the data into Elasticsearch
        es.index(
            index='sensor_data',  # Elasticsearch index name
            body={
                'sensor_id': sensor_data['sensor_id'],
                'temperature': sensor_data['temperature'],
                'humidity': sensor_data['humidity'],
                'timestamp': iso_timestamp  # Use ISO 8601 timestamp format
            }
        )
    except Exception as e:
        print(f"Failed to index data: {e}")


def consume_data():
    # Initialize the Elasticsearch client
    es = Elasticsearch(['http://43.88.102.118:9200'])

    # Create a Kafka consumer
    consumer = KafkaConsumer(
        'sensor_data',
        bootstrap_servers='localhost:9092',
        auto_offset_reset='earliest',
        group_id='sensor-group',
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )


    for message in consumer:
        sensor_data = message.value
        
        # Index the data into Elasticsearch
        index_to_elasticsearch(es, sensor_data)
        print(f"Indexed to Elasticsearch: {sensor_data}")

    
dag = DAG(
    dag_id = "sensor_data_consumer",
    default_args = {
        "owner" : "Prabakar Sundar",
        "start_date" : airflow.utils.dates.days_ago(1),
    },
    schedule_interval = "@yearly",
    catchup = False
)

start = PythonOperator(
    task_id = "start",
    python_callable = lambda: print("Jobs Started"),
    dag=dag
)

python_job = PythonOperator(
    task_id="sensor_data_consumer",
    python_callable=consume_data,
    dag=dag
)

end = PythonOperator(
    task_id="end",
    python_callable = lambda: print("Jobs completed successfully"),
    dag=dag
)

start >> python_job >> end