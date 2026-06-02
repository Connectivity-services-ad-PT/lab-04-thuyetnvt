# Docker Readiness Checklist

## Dockerfile

- [x] Uses a reasonable base image: `python:3.11-slim`.
- [x] Defines `WORKDIR`.
- [x] Copies dependency file before source to use build cache.
- [x] Exposes port `8000`.
- [x] Defines `CMD`.
- [x] Defines `HEALTHCHECK` for `GET /health`.
- [x] Runs as non-root user `appuser`.
- [x] Does not contain real secrets.

## Runtime

- [x] Container can run from image `fit4110/ai-vision:lab04`.
- [x] Port mapping is `8000:8000`.
- [x] `/health` returns `200`.
- [x] Runtime config is supplied through `.env.example`.

## Testing

- [x] Lab 03-style Postman collection runs against the container.
- [x] Newman reports are generated in `reports/`.
- [x] Functional tests pass.
- [x] Auth tests pass on local/container.
- [x] Negative tests pass on local/container.
- [x] Boundary and reliability tests pass.

## Evidence

- [x] Docker build log exists.
- [x] Docker health evidence exists.
- [x] Newman HTML/XML report exists.
- [x] Image tag is documented.
