Pathway POC: High-Performance Data Processing on Minikube
This Proof of Concept (POC) demonstrates a modern streaming architecture using Pathway to overcome common limitations in serverless streaming (like Nuclio) and batch processing (like PySpark).
🚀 Key Features Addressed
Connection Efficiency: Uses Pathway’s internal engine to prevent exponential DB connection growth.
Backpressure Handling: Native Kafka integration manages ingestion rates to protect DB health.
High Concurrency: Optimized for Kafka Partitioning (10 partitions) with multi-instance consumers.
Unified Stack: Replaces fragmented batch/streaming jobs with a single Python-based Pathway logic.
Exactly-Once Semantics: Reliable event processing without duplicates.
🛠 Prerequisites
Minikube installed.
Docker Desktop (allocated at least 8GB RAM / 4 CPUs).
Helm and kubectl installed.
🏗 Setup Instructions
1. Environment Cleanup (Fresh Start)
Ensure no legacy components interfere with the KRaft mode installation.
bash
minikube stop && minikube delete --all --purge
docker system prune -a -f --volumes
rm -rf ~/poc-pathway
Use code with caution.

2. Initialize Minikube
bash
minikube start --driver=docker --cpus=4 --memory=7000mb --kubernetes-version=stable
eval $(minikube docker-env)  # Connects local shell to Minikube's Docker daemon
Use code with caution.

3. Install Strimzi Kafka (v0.49.1)
bash
kubectl create namespace kafka
helm repo add strimzi https://strimzi.io/charts/
helm repo update
helm install strimzi-kafka-operator strimzi/strimzi-kafka-operator --namespace kafka --version 0.49.1
Use code with caution.

4. Deploy Kafka KRaft Cluster & Topic
Deploy a 10-partition topic to test high-concurrency event processing.
bash
# Apply Kafka Cluster (KRaft Mode)
kubectl apply -f kafka-kraft.yaml -n kafka

# Apply 10-Partition Topic
kubectl apply -f kafka-topic.yaml -n kafka
Use code with caution.

5. Database Setup
Deploy Postgres and initialize the schema.
bash
kubectl apply -f postgres.yaml
# Wait for pod to be ready, then create table:
kubectl exec -it postgres-0 -- psql -U user -d db -c \
"CREATE TABLE events (user_id TEXT, count INT, total_value DOUBLE PRECISION, time BIGINT);"
Use code with caution.

📦 Application Deployment
6. Build Pathway Images
Build your logic locally within the Minikube environment.
bash
cd poc-pathway
docker build -f Dockerfile-consumer -t pathway-consumer:latest .
docker build -f Dockerfile-producer -t pathway-producer:latest .
Use code with caution.

7. Launch Consumer Scalability
Deploy 3 replicas to demonstrate how Pathway shares load across Kafka partitions.
bash
kubectl apply -f pathway-deployment.yaml
kubectl scale deployment/pathway-consumer --replicas=3
Use code with caution.

🧪 Testing & Validation
Run Data Producer
bash
# Forward Kafka port to local machine
kubectl port-forward svc/my-cluster-kafka-bootstrap -n kafka 9092:9092

# Run the producer script
python producer.py
Use code with caution.

Monitor Results
Action	Command
Check Logs	kubectl logs -l app=pathway-consumer -f
Check DB Count	kubectl exec -it postgres-0 -- psql -U user -d db -c "SELECT COUNT(*) FROM events;"
Reset Data	kubectl exec -it postgres-0 -- psql -U user -d db -c "TRUNCATE TABLE events RESTART IDENTITY;"
📝 Manual Configuration Notes
[!IMPORTANT]
Bootstrap Servers: Ensure consumer.py uses my-cluster-kafka-bootstrap.kafka.svc.cluster.local:9092.
Database URL: Ensure the connection string in consumer.py is postgresql://user:password@postgres:5432/db.
Memory Limits: If pods crash with OOM, increase Minikube memory to 8192mb.
📊 Feature Comparison Matrix (Pathway vs. Others)
Feature	Pathway (This POC)	Nuclio / Serverless
DB Connections	Constant (Optimized)	Exponential (per replica)
Backpressure	Native Kafka throttling	None (Risks DB exhaustion)
Windowing	First-class SQL-like support	Limited / Manual
Scale-out	Partition-aware consumers	Function-level only
Maintenance	Single Python code-base	Fragmented (Nuclio/Spark/Python)
