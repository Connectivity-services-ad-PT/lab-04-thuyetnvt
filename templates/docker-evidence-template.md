# Docker Evidence - Lab 04

## Team

- Team name: team-camera-ai-vision
- Service: ai-vision
- Image tag: `fit4110/ai-vision:lab04`

## 1. Build evidence

Command:

```bash
docker build -t fit4110/ai-vision:lab04 .
```

Evidence path:

```text
reports/docker-build.log
```

## 2. Run evidence

Command:

```bash
docker run --rm -p 8000:8000 --env-file .env.example fit4110/ai-vision:lab04
```

## 3. Healthcheck evidence

Command:

```bash
curl http://localhost:8000/health
```

Evidence path:

```text
reports/docker-health.txt
```

## 4. Newman evidence

Command:

```bash
npm run test:local
```

Report paths:

```text
reports/newman-lab04-local.html
reports/newman-lab04-local.xml
```

## 5. Notes

- Known limitation: AI detection is a lightweight mock model for Lab 04 packaging; no heavy YOLO model is bundled.
- Next step for Lab 05: compose AI Vision with Camera Stream/Core services.
