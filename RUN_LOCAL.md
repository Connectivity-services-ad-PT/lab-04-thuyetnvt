# RUN_LOCAL.md - Lab 04 AI Vision

This repo packages the Pair 01 AI Vision provider service in Docker and verifies it with the Lab 03 Postman/Newman tests.

## 1. Install Node dependencies

```bash
npm install
```

## 2. Build Docker image

```bash
docker build -t fit4110/ai-vision:lab04 .
```

## 3. Run container

```bash
docker run --rm \
  --name fit4110-ai-vision-lab04 \
  -p 8000:8000 \
  --env-file .env.example \
  fit4110/ai-vision:lab04
```

Expected health response:

```bash
curl http://localhost:8000/health
```

```json
{
  "status": "ok",
  "service": "ai-vision",
  "time": "2026-06-02T00:00:00Z"
}
```

## 4. Run Newman against the container

Open another terminal while the container is running:

```bash
npm run test:local
```

Reports are generated at:

```text
reports/newman-lab04-local.xml
reports/newman-lab04-local.html
```

## 5. Stop container

If the container is running in detached mode:

```bash
docker stop fit4110-ai-vision-lab04
```

## Quick commands

```bash
make build
make run
make test-docker
make stop
```
