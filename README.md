
# Containerized AI Document Summarization Pipeline

A microservices-based NLP document processing pipeline that ingests multi-format documents (PDF, DOCX, TXT), extracts and normalizes text, and generates abstractive summaries using locally containerized Hugging Face transformer models.

Built with **FastAPI, Python, Hugging Face Transformers, Redis, Docker, Docker Compose, and Kubernetes**, the pipeline uses asynchronous job queues to decouple document ingestion from computationally intensive AI inference.

## Architecture Overview

The pipeline separates document processing into independent, loosely coupled services, improving modularity, scalability, and maintainability.

```text
                   +----------------------+
                   |      Client / UI     |
                   +----------+-----------+
                              |
                       POST /upload
                              |
                              v
                   +----------------------+
                   |   FastAPI Gateway    |
                   +----------+-----------+
                              |
                 +------------+------------+
                 |                         |
                 v                         v
       +------------------+      +------------------+
       | Shared Storage   |      |   Redis Queue    |
       | /shared/uploads  |      | doc_processing   |
       | /shared/cleaned  |      | summarization    |
       | /shared/summaries|      +--------+---------+
       +--------+---------+               |
                ^                         v
                |              +----------------------+
                +--------------|  Ingestion Worker    |
                               +----------+-----------+
                                          |
                                   Cleaned Text
                                          |
                                          v
                               +----------------------+
                               | Summarization Worker|
                               | Hugging Face Models  |
                               +----------+-----------+
                                          |
                                          v
                               +----------------------+
                               | Final Summary        |
                               | Shared Storage       |
                               +----------------------+
```

### Core Services

1. **API Gateway (`gateway-service`)** — A FastAPI service exposing REST endpoints for document uploads, job-status polling, and health checks. Generates unique job IDs, stores uploaded documents, and queues processing tasks.

2. **Ingestion Service (`ingestion-service`)** — An asynchronous worker that extracts text from PDF, DOCX, and TXT files, normalizes whitespace and non-printable characters, and queues the cleaned text for summarization.

3. **Summarization Service (`summarization-service`)** — A worker that runs Hugging Face sequence-to-sequence transformer models locally. Implements token-aware text chunking and combines chunk summaries for longer documents.

4. **Redis** — Acts as the message broker and job-metadata store, enabling asynchronous processing without blocking HTTP requests.

5. **Shared Storage** — A shared filesystem mounted across services for exchanging uploaded files, cleaned text, and generated summaries.

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| API Gateway | FastAPI, Uvicorn, Pydantic | REST APIs and file uploads |
| Document Processing | PyPDF, python-docx | Text extraction and normalization |
| AI Inference | PyTorch, Hugging Face Transformers | Local transformer inference |
| Summarization Model | `google-t5/t5-small` | Abstractive text summarization |
| Message Broker | Redis 7 Alpine | Queues and job metadata |
| Containerization | Docker, Docker Compose | Service isolation and local orchestration |
| Orchestration | Kubernetes, Minikube | Deployments, storage, and scaling |

## Project Structure

```text
summarizer-pipeline/
├── gateway-service/
│   ├── app/
│   │   ├── main.py
│   │   └── schemas.py
│   ├── Dockerfile
│   └── requirements.txt
├── ingestion-service/
│   ├── app/
│   │   ├── extractor.py
│   │   └── worker.py
│   ├── Dockerfile
│   └── requirements.txt
├── summarization-service/
│   ├── app/
│   │   ├── model.py
│   │   └── worker.py
│   ├── Dockerfile
│   └── requirements.txt
├── shared-storage/
│   ├── uploads/
│   ├── cleaned/
│   └── summaries/
├── k8s/
│   ├── storage.yaml
│   ├── configmap.yaml
│   ├── redis.yaml
│   ├── gateway.yaml
│   ├── ingestion.yaml
│   ├── summarization.yaml
│   └── hpa.yaml
├── docker-compose.yml
└── README.md
```

## Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) v24 or later
- Docker Compose v2 or later
- Git

### Run with Docker Compose

Clone the repository and navigate to the project directory:

```bash
git clone <your-repository-url>
cd summarizer-pipeline
```

Build the images and start the services:

```bash
docker compose up --build -d
```

Check the running containers:

```bash
docker compose ps
```

View service logs:

```bash
docker compose logs -f
```

Access the interactive Swagger API documentation:

**http://localhost:8000/docs**

> Ensure that the gateway is mapped to port `8000` in your Docker Compose configuration.

## API Reference

### 1. Upload a Document

**Endpoint:** `POST /upload`

**Content-Type:** `multipart/form-data`

Accepts PDF, DOCX, or TXT documents for asynchronous processing.

Example using cURL:

```bash
curl -X POST "http://localhost:8000/upload" \
  -F "file=@annual_report.pdf"
```

Example response (`202 Accepted`):

```json
{
  "job_id": "feff23ab-24aa-4041-8b39-4352b8b001e3",
  "filename": "annual_report.pdf",
  "status": "queued",
  "message": "Document uploaded and job queued successfully.",
  "created_at": "2026-10-29T00:01:25.102"
}
```

### 2. Check Job Status

**Endpoint:** `GET /status/{job_id}`

Retrieve the processing status and the generated summary when processing is complete.

```bash
curl "http://localhost:8000/status/<job_id>"
```

Example response (`200 OK`):

```json
{
  "job_id": "feff23ab-24aa-4041-8b39-4352b8b001e3",
  "status": "completed",
  "error": null,
  "summary": "This document outlines the transition to cloud-native microservices...",
  "created_at": "2026-10-29T00:01:25.102"
}
```

Possible job statuses include `queued`, `processing`, `completed`, and `failed`, depending on the implementation.

### 3. Health Check

**Endpoint:** `GET /health`

Checks the gateway's health.

```bash
curl "http://localhost:8000/health"
```

Example response:

```json
{
  "status": "healthy",
  "timestamp": "2026-10-29T00:05:00.000"
}
```

## Kubernetes Deployment

The pipeline can be deployed to a local Kubernetes cluster using Minikube.

### 1. Start Minikube

```bash
minikube start --cpus=4 --memory=8192
```

### 2. Configure the Docker Environment

For Docker driver setups that support the legacy Docker environment command:

```bash
eval $(minikube docker-env)
```

Alternatively, build the images locally and load them into Minikube:

```bash
docker build -t summarizer-gateway:latest ./gateway-service
docker build -t summarizer-ingestion:latest ./ingestion-service
docker build -t summarizer-ai:latest ./summarization-service

minikube image load summarizer-gateway:latest
minikube image load summarizer-ingestion:latest
minikube image load summarizer-ai:latest
```

If you use the image-loading approach, ensure the Kubernetes deployments use the matching image names and an appropriate `imagePullPolicy`, such as `IfNotPresent`.

### 3. Apply Kubernetes Manifests

Apply the manifests in dependency order:

```bash
kubectl apply -f k8s/storage.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/gateway.yaml
kubectl apply -f k8s/ingestion.yaml
kubectl apply -f k8s/summarization.yaml
kubectl apply -f k8s/hpa.yaml
```

### 4. Verify the Deployment

```bash
kubectl get pods
kubectl get services
kubectl get deployments
```

Expose the gateway:

```bash
minikube service gateway-service
```

> **Note:** Kubernetes storage access modes and dynamic provisioning depend on the cluster's storage provisioner. Verify that the configured PersistentVolume and PersistentVolumeClaim support the access pattern required by your services. Horizontal Pod Autoscaling also requires appropriate resource requests and a metrics provider.

## Configuration

Configure services through environment variables.

| Variable | Example Default | Description |
|---|---|---|
| `REDIS_HOST` | `redis` | Redis hostname inside the container network |
| `REDIS_PORT` | `6379` | Redis TCP port |
| `MODEL_NAME` | `google-t5/t5-small` | Hugging Face model identifier |
| `UPLOAD_DIR` | `/shared/uploads` | Uploaded document directory |
| `CLEANED_DIR` | `/shared/cleaned` | Normalized text directory |
| `SUMMARIES_DIR` | `/shared/summaries` | Generated summary directory |

For larger models, such as `facebook/bart-large-cnn`, consider the additional memory and CPU requirements before scaling the summarization workers.

## Key Features

- **Microservices Architecture:** Separates API handling, document ingestion, and AI inference into independently deployable services.
- **Multi-Format Document Processing:** Supports PDF, DOCX, and TXT input formats.
- **Asynchronous Processing:** Uses Redis queues to decouple uploads from compute-intensive summarization.
- **Local AI Inference:** Runs Hugging Face transformer models within containers.
- **Long-Document Handling:** Uses token-aware chunking to process documents exceeding model input limits.
- **Shared File Storage:** Exchanges intermediate artifacts between containers through mounted storage.
- **Containerized Deployment:** Supports local development using Docker Compose and Kubernetes.
- **Operational Visibility:** Provides job-status tracking, service logs, and a health endpoint.

## Stopping the Pipeline

Stop and remove the containers while preserving named volumes:

```bash
docker compose down
```

Stop the containers and remove Compose-managed named volumes:

```bash
docker compose down -v
```

> **Warning:** The `-v` option can permanently delete data stored in named volumes. Bind-mounted files in the project directory may remain, depending on the Compose configuration.

## Future Improvements

- Add authentication, authorization, and upload-size limits.
- Introduce retry policies, dead-letter queues, and idempotent job processing.
- Add structured logging, metrics, and distributed tracing.
- Improve summary quality through configurable models and chunk-merging strategies.
- Add automated tests and CI/CD workflows.
- Support object storage and production-grade persistent queue infrastructure.
