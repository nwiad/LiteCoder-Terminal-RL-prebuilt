## Multi-Arch Docker Image for a Go Microservice

Create a complete build setup for a Go HTTP microservice that supports multi-architecture Docker images targeting both `linux/amd64` and `linux/arm64`.

### Technical Requirements

- Language: Go 1.21+
- All project files must be created under `/app/`

### Project Structure

Create the following files:

1. `/app/go.mod` — Go module file with module name `multiarch-service`.
2. `/app/main.go` — A simple HTTP server (see specification below).
3. `/app/Dockerfile` — Multi-stage Dockerfile for multi-arch builds.
4. `/app/docker-compose.yml` — Compose file for local testing.
5. `/app/build.sh` — Shell script that builds the multi-arch image using `docker buildx`.

### Go Application (`main.go`)

- The HTTP server must listen on port `8080`.
- It must expose the following endpoints:
  - `GET /` — Returns a JSON response: `{"service":"multiarch-service","status":"running"}` with `Content-Type: application/json`.
  - `GET /arch` — Returns a JSON response containing the runtime architecture info: `{"os":"<runtime.GOOS>","arch":"<runtime.GOARCH>"}` with `Content-Type: application/json`. Use Go's `runtime` package to obtain these values.
  - `GET /health` — Returns HTTP 200 with JSON body: `{"healthy":true}`.
- The server must handle graceful shutdown on `SIGINT` and `SIGTERM` signals.

### Dockerfile

- Must use a multi-stage build:
  - **Builder stage**: Use `golang:1.21-alpine` (or later patch) as the base. Compile the Go binary with `CGO_ENABLED=0`. The `TARGETOS` and `TARGETARCH` build arguments must be used for cross-compilation via `GOOS` and `GOARCH` environment variables.
  - **Runtime stage**: Use `alpine:3.18` (or later patch) as the base. Copy only the compiled binary from the builder stage. Expose port `8080`. The container must run as a non-root user.
- The Dockerfile must contain a `HEALTHCHECK` instruction that checks the `/health` endpoint.

### Build Script (`build.sh`)

- Must be executable (shebang `#!/bin/bash` or `#!/usr/bin/env bash`).
- Must create a buildx builder instance if one does not already exist.
- Must build for platforms `linux/amd64,linux/arm64`.
- Must tag the image as `multiarch-service:latest`.
- Must accept an optional `--push` flag: when provided, the image is pushed; otherwise it is loaded locally (or uses `--output type=image`).

### Docker Compose (`docker-compose.yml`)

- Must define a service named `multiarch-service`.
- The service must use image `multiarch-service:latest`.
- Must map host port `8080` to container port `8080`.
- Must include a `healthcheck` configuration that targets the `/health` endpoint.
- Must define a `restart` policy of `unless-stopped`.
