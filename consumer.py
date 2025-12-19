import pathway as pw
from datetime import timedelta
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    filename='pathway_consumer.log',
    filemode='w',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 1. Schema Definition
class EventSchema(pw.Schema):
    user_id: str  
    event_type: str
    timestamp: str 
    value: str     
    payload: str

def create_kafka_reader(group_id):
    logger.info(f"Creating Kafka reader for group {group_id}")
    reader = pw.io.kafka.read(
        rdkafka_settings={
            "bootstrap.servers": "127.0.0.1:9094",
            "group.id": group_id,
            "enable.auto.commit": "false"
        },
        topic="events",
        format="json",
        schema=EventSchema,
        parallel_readers=3
    )
    
    # Use built-in operators for casting and parsing
    # FIX: Native Operators (No UDFs)
    reader = reader.with_columns(
        # 1. Native numeric methods are stable for 2025
        user_id_int=pw.this.user_id.as_int(),  
        float_value=pw.this.value.as_float(),
        
        # 2. Try native datetime parsing method
        # If your version is recent, this is the most direct path:
        parsed_ts=pw.this.timestamp.dt.parse_iso8601(),
        
        # 3. Native string concatenation using '+'
        temp_hash=pw.this.user_id + "_" + pw.this.timestamp
    )
    return reader


# Initialize consumers
kafka1 = create_kafka_reader("pathway-group-1")

def windowed_aggregation(kafka):
    return (
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
    )

windowed1 = windowed_aggregation(kafka1)

# SQL Output
postgres_config = {
    "host": "localhost", "port": "5432", "dbname": "pocevents",
    "user": "pocuser", "password": "pocpass"
}

pw.io.postgres.write(windowed1, postgres_settings=postgres_config, table_name="events")

if __name__ == "__main__":
    # CONTROL MINIBATCHES: Use pw.run parameters for 2025
    pw.run(minibatch_size=6, minibatch_duration_ms=100)
