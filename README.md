# FIT4110 Lab 04 - Dockerized AI Vision

Course: FIT4110 - Connectivity Services and Platform Technologies  
Lab: 04 - Docker packaging and Newman verification  
Case study: Smart Campus Operations Platform

## Current Submission

This repo packages the Pair 01 provider service from Lab 02 and Lab 03:

- Consumer: Camera Stream (B2)
- Provider: AI Vision (B4)
- Contract: `contracts/ai-vision.openapi.yaml`
- Service implementation: `src/ai_vision_app/main.py`
- Docker image tag: `fit4110/ai-vision:lab04`
- Postman collection: `postman/collections/FIT4110_lab04_ai_vision_docker.postman_collection.json`
- Local/docker environment: `postman/environments/FIT4110_lab04_local.postman_environment.json`

## Main Flow

```text
OpenAPI Contract
-> AI Vision service
-> Dockerfile
-> Docker image
-> Docker container
-> Newman tests on container
-> Evidence in reports/
```

## Requirements

- Docker Desktop or Docker Engine
- Node.js 20+
- npm

## Install Test Dependencies

```bash
npm install
```

## Build Image

```bash
docker build -t fit4110/ai-vision:lab04 .
```

## Run Container

```bash
docker run --rm \
  --name fit4110-ai-vision-lab04 \
  -p 8000:8000 \
  --env-file .env.example \
  fit4110/ai-vision:lab04
```

## Health Check

```bash
curl http://localhost:8000/health
```

Expected:

```json
{
  "status": "ok",
  "service": "ai-vision",
  "time": "2026-06-02T00:00:00Z"
}
```

## Run Newman Against Container

```bash
npm run test:local
```

Generated evidence:

```text
reports/newman-lab04-local.xml
reports/newman-lab04-local.html
```

## What Is Tested

- `GET /health`
- `POST /vision/detect`
- `GET /vision/detections/{detectionId}`
- `GET /vision/models/info`
- Auth success/failure
- Invalid payload and boundary cases
- `409 Conflict` for idempotency conflict
- `503 ServiceUnavailable` for model unavailable behavior
- Local/container response-time check

## Docker Requirements Covered

- Multi-stage Dockerfile
- `.dockerignore`
- `.env.example`
- Non-root runtime user
- `HEALTHCHECK`
- Re-runnable instructions in `RUN_LOCAL.md`
- Newman XML/HTML evidence
