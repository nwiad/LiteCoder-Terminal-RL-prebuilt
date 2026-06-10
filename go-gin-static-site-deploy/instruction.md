## Build & Deploy a Static Golang Website

Set up a Go web application using the Gin framework with a complete build, development, and production pipeline including live-reload, multi-stage Docker builds, docker-compose, and a Makefile.

### Technical Requirements

- Language: Go 1.21+
- Framework: Gin (`github.com/gin-gonic/gin`)
- Working directory: `/app`

### Project Structure

Create the following files under `/app`:

```
/app/
├── main.go
├── go.mod
├── go.sum
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── README.md
└── .air.toml
```

### 1. Go Application (`main.go`)

Create a Go web server using the Gin framework that:
- Listens on port `8080`
- Serves a `GET /` route that returns HTTP 200 with an HTML response containing the text `Welcome to the Landing Page`
- Serves a `GET /health` route that returns HTTP 200 with JSON `{"status":"ok"}`
- The Go module name in `go.mod` must be `landing-page`

### 2. Dockerfile

Create a multi-stage Dockerfile at `/app/Dockerfile` with:
- A builder stage named `builder` that uses a `golang` base image, compiles the Go binary with `CGO_ENABLED=0`, and produces a binary named `server`
- A final stage that uses `scratch` as the base image
- The final stage must `COPY` the compiled binary from the builder stage
- The final stage must `EXPOSE 8080`
- The `ENTRYPOINT` or `CMD` must run the `server` binary

### 3. docker-compose.yml

Create `/app/docker-compose.yml` that defines:
- A service named `web`
- The `web` service must map host port `8080` to container port `8080`
- The `web` service must include a `build` context pointing to the current directory

### 4. Makefile

Create `/app/Makefile` with the following targets:
- `dev`: runs `docker compose up` (with or without additional flags like `--build` or `--watch`)
- `ship`: runs a docker build and docker push command (the push destination can be any registry/repo placeholder)
- `build`: compiles the Go binary locally using `go build`

### 5. Configuration

Create `/app/.air.toml` as a configuration file for the `air` live-reload tool. It must contain at minimum:
- A `[build]` section
- A `cmd` key within `[build]` that specifies a Go build command
- A `bin` key within `[build]` that specifies the output binary path

### 6. README.md

Create `/app/README.md` that documents the project. It must contain all of the following sections (as markdown headings at any level):
- A section titled `Development` describing how to run locally
- A section titled `Production` describing how to build/deploy
- A section titled `Commands` listing available make targets
