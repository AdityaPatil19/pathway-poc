import pathway as pw
from datetime import timedelta
import logging

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    filename='pathway_consumer.log',
    filemode='w',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Schema
class EventSchema(pw.Schema):
    user_id: str  
    event_type: str
    timestamp: str 
    value: str     
    payload: str

def create_kafka_reader(group_id: str):
    logger.info(f"Creating Kafka reader for group: {group_id}")
   
    reader = pw.io.kafka.read(
        rdkafka_settings={
            "bootstrap.servers": "127.0.0.1:9094",
            "group.id": group_id,
            "enable.auto.commit": "false",
            "auto.offset.reset": "earliest"
        },
        topic="events",
        format="json",
        schema=EventSchema,
        autocommit_duration_ms=5000
    )
   
    reader = reader.with_columns(
        user_id_int=pw.this.user_id.str.parse_int(),
        float_value=pw.this.value.str.parse_float(),
        parsed_ts=pw.this.timestamp.dt.strptime("%Y-%m-%dT%H:%M:%S.%f"),
        temp_hash=pw.this.user_id + "_" + pw.this.timestamp
    )
    return reader

# 3 independent consumer groups
kafka_group1 = create_kafka_reader("pathway-group-demo-1")
kafka_group2 = create_kafka_reader("pathway-group-demo-2")
kafka_group3 = create_kafka_reader("pathway-group-demo-3")

def windowed_aggregation(kafka, group_name: str):
    aggregated = (
        kafka
        .windowby(
            kafka.parsed_ts,
            window=pw.temporal.tumbling(duration=timedelta(minutes=1)),
            instance=kafka.user_id_int
        )
        .reduce(
            user_id=pw.this._pw_instance,
            count=pw.reducers.count(),
            total_value=pw.reducers.sum(pw.this.float_value),
            event_hash=pw.reducers.any(pw.this.temp_hash)
        )
        .filter(pw.this.count <= 1000)
        .with_columns(consumer_group=group_name)  # Add constant tag
    )
    return aggregated

# Apply aggregation per group
windowed1 = windowed_aggregation(kafka_group1, "demo-group-1")
windowed2 = windowed_aggregation(kafka_group2, "demo-group-2")
windowed3 = windowed_aggregation(kafka_group3, "demo-group-3")

# Write each group's output to the SAME table (Pathway handles incremental upserts)
# Since schemas are identical (including consumer_group), writes merge naturally
pw.io.postgres.write(windowed1, postgres_settings={
    "host": "localhost",
    "port": "5432",
    "dbname": "pocevents",
    "user": "pocuser",
    "password": "pocpass"
}, table_name="events_multi_group")

pw.io.postgres.write(windowed2, postgres_settings={
    "host": "localhost",
    "port": "5432",
    "dbname": "pocevents",
    "user": "pocuser",
    "password": "pocpass"
}, table_name="events_multi_group")

pw.io.postgres.write(windowed3, postgres_settings={
    "host": "localhost",
    "port": "5432",
    "dbname": "pocevents",
    "user": "pocuser",
    "password": "pocpass"
}, table_name="events_multi_group")

if __name__ == "__main__":
    logger.info("Starting Pathway with 3 independent consumer groups writing to same table...")
    pw.run()
