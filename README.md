# pathway-poc
pathway poc on minikube for data processing

1. Clean Up Everything (Fresh Start)
minikube stop
minikube delete --all --purge
docker system prune -a -f --volumes  # Caution: Removes all Docker data
rm -rf ~/poc-pathway  # Delete old POC directory if exists

2. Start Minikube with Adequate Resources
minikube start --driver=docker --cpus=4 --memory=7000mb --kubernetes-version=stable
eval $(minikube docker-env)  # Enable local Docker builds for Minikube

Verify:
minikube status  # Should show "Running"
kubectl cluster-info

3. Install Strimzi Kafka Operator 0.49.1
helm repo add strimzi https://strimzi.io/charts/
helm repo update
kubectl create namespace kafka
helm install strimzi-kafka-operator strimzi/strimzi-kafka-operator --namespace kafka --version 0.49.1

Verify:
kubectl get pods -n kafka -w  # Wait for strimzi-cluster-operator pod to be Running/1/1
kubectl get crd | grep kafka  # Should list Kafka, KafkaNodePool, etc.

4. Deploy Kafka Cluster in KRaft Mode (Single-Node Dual-Role)
Create kafka-kraft.yaml with this exact content (uses official pattern: annotations for KRaft/node-pools, label linking, shared metadata storage, Kafka 3.8.0 as requested):
YAMLapiVersion: kafka.strimzi.io/v1
kind: Kafka
metadata:
  name: my-cluster
  namespace: kafka
  annotations:
    strimzi.io/node-pools: enabled
    strimzi.io/kraft: enabled
spec:
  kafka:
    version: "3.8.0"
    metadataVersion: "3.8-IV0"  # String format
    listeners:
      - name: plain
        port: 9092
        type: internal
        tls: false
    config:
      offsets.topic.replication.factor: "1"
      transaction.state.log.replication.factor: "1"
      transaction.state.log.min.isr: "1"
      default.replication.factor: "1"
      min.insync.replicas: "1"
      auto.create.topics.enable: "true"
  entityOperator:
    topicOperator: {}
    userOperator: {}
---
apiVersion: kafka.strimzi.io/v1
kind: KafkaNodePool
metadata:
  name: dual
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
spec:
  replicas: 1
  roles:
    - broker
    - controller
  storage:
    type: jbod
    volumes:
      - id: 0
        type: persistent-claim
        size: 5Gi
        deleteClaim: false
        kraftMetadata: shared  # Shares metadata on this volume

Apply:
kubectl apply -f kafka-kraft.yaml -n kafka


5. Create Multi-Partition Kafka Topic
Use your kafka-topic.yaml (10 partitions):
apiVersion: kafka.strimzi.io/v1
kind: KafkaTopic
metadata:
  name: my-topic
  namespace: kafka
  labels:
    strimzi.io/cluster: my-cluster
spec:
  partitions: 10
  replicas: 1
kubectl apply -f kafka-topic.yaml -n kafka

Verify:kubectl get kafkatopic my-topic -n kafka  # Partitions: 10

6. Deploy Postgres DB
Use your postgres.yaml (as provided earlier).
kubectl apply -f postgres.yaml
kubectl exec -it postgres-0 -- psql -U user -d db -c "CREATE TABLE events (id SERIAL PRIMARY KEY, data TEXT);"

Verify:kubectl get pods  # postgres-0 Running
kubectl get svc postgres  # Service exists

7. Prepare Pathway Code and Build Docker Images
Create directory poc-pathway with files (requirements.txt, producer.py, consumer.py, Dockerfile-consumer, Dockerfile-producer) as provided in initial response.
MANUAL CHANGES:

In producer.py and consumer.py: Update bootstrap to the value from Step 4.
In consumer.py: Update DB URL to postgresql://user:password@postgres:5432/db.

Build (with Minikube Docker env active):
cd poc-pathway
docker build -f Dockerfile-consumer -t pathway-consumer:latest .
docker build -f Dockerfile-producer -t pathway-producer:latest .

Verify:docker images | grep pathway  # Images listed

8. Deploy Pathway Consumer (Multiple Instances)
Use your pathway-deployment.yaml (replicas: 3 for concurrency demo).
kubectl apply -f pathway-deployment.yaml

Verify:kubectl get pods  # 3 pathway-consumer pods Running
kubectl get deployment pathway-consumer  # Replicas: 3
kubectl logs -f <one-pod-name>  # Check for Pathway startup/no errors

9. Run Producer and Test POC
Option 1 (Local run with port-forward):
kubectl port-forward svc/my-cluster-kafka-bootstrap -n kafka 9092:9092
python producer.py  # In another terminal; send events
Option 2 (Deploy as Job):
Create producer-job.yaml (kind: Job, image: pathway-producer:latest).
kubectl apply -f producer-job.yaml

Verify All Points:kubectl logs -f deployment/pathway-consumer  # Event-level processing, windowing, rate limiting
kubectl port-forward svc/postgres 5432:5432
psql -h localhost -U user -d db -c "SELECT COUNT(*) FROM events;"  # Data inserted, no connection exhaustion
kubectl scale deployment/pathway-consumer --replicas=5  # Scale; check logs/DB (pooling prevents exhaustion)
kubectl top pods  # Resource usage stable

This sequence cov

  
