import json
import random
from datetime import datetime
from kafka import KafkaProducer
from jinja2 import Template

# Load template
with open('sample_event.json', 'r') as f:
    template_str = f.read()
template = Template(template_str)

# Kafka producer (idempotent for exactly-once)
producer = KafkaProducer(
#    bootstrap_servers=['192.168.49.2:31933'],  # From minikube service
    bootstrap_servers=['127.0.0.1:9094'],  # From minikube service
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    acks='all',  # For durability
    enable_idempotence=True  # Exactly-once semantics
)

# Generate 100k events
for i in range(500000):
    event = template.render(
        random_int=lambda minv, maxv: random.randint(minv, maxv),
        random_choice=lambda choices: random.choice(choices),
        now=lambda: datetime.now().isoformat(),
        random_float=lambda minv, maxv: round(random.uniform(minv, maxv), 2),
        random_string=lambda length: ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=length))
    )
    event_data = json.loads(event)
    producer.send('events', value=event_data)
    if i % 10000 == 0:
        print(f"Sent {i} events")

producer.flush()
print("All 100k events produced.")
