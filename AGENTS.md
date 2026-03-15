# AGENTS.md

## Overview

miniflux-ai is a Python/Flask application that integrates with [Miniflux](https://miniflux.app/) RSS reader to enhance feed entries with LLM-generated summaries, translations, and daily news digests. See `README.md` for full details.

## Cursor Cloud specific instructions

### Services

| Service | Purpose | How to run |
|---------|---------|------------|
| PostgreSQL 17 | Database for Miniflux | Docker container (see below) |
| Miniflux | RSS reader that the app integrates with | Docker container (see below) |
| miniflux-ai | This application (Flask + scheduler) | `sudo python3 main.py` (needs root for port 80) |
| LLM endpoint | AI processing backend | External (OpenAI-compatible API) or mock for dev |

### Starting infrastructure (Docker required)

```bash
# Create network
docker network create miniflux-net

# Start PostgreSQL with "db" alias (Miniflux references host "db")
docker run -d --name postgres --network miniflux-net --network-alias db \
  -e POSTGRES_USER=miniflux -e POSTGRES_PASSWORD=secret -e POSTGRES_DB=miniflux \
  --health-cmd="pg_isready -U miniflux" --health-interval=10s --health-start-period=30s \
  postgres:17-alpine

# Wait for PG, then start Miniflux
sleep 5
docker run -d --name miniflux --network miniflux-net -p 8080:8080 \
  -e "DATABASE_URL=postgres://miniflux:secret@db/miniflux?sslmode=disable" \
  -e RUN_MIGRATIONS=1 -e CREATE_ADMIN=1 -e ADMIN_USERNAME=admin -e ADMIN_PASSWORD=test123 \
  -e FETCHER_ALLOW_PRIVATE_NETWORKS=1 -e INTEGRATION_ALLOW_PRIVATE_NETWORKS=1 \
  miniflux/miniflux:latest
```

### Gotchas

- **docker-compose.yml has a service name mismatch**: The Miniflux service `depends_on: db` but the Postgres service is named `postgres`. When running containers manually, add `--network-alias db` to the PostgreSQL container.
- **Port 80**: `main.py` hardcodes Flask to port 80, requiring root. Run with `sudo python3 main.py`.
- **config.yml required at startup**: The app reads `config.yml` at module import time (in `common/config.py`). Copy from `config.sample.English.yml` or `config.sample.Chinese.yml` and adjust Miniflux URL, API key, and LLM settings.
- **Miniflux API key**: Create via `curl -X POST http://localhost:8080/v1/api-keys -u admin:test123 -H "Content-Type: application/json" -d '{"description":"dev"}'`.
- **Unit test bug**: `tests/test_filter.py` has a pre-existing bug — it passes a plain dict to `filter_entry()` which expects a `Config` object with `.agents` attribute. The test will fail with `AttributeError`.
- **No lint tooling configured**: The repo has no linter config (no flake8, ruff, pylint, mypy). Standard Python syntax checking applies.
- **LLM endpoint**: For dev testing without a real LLM, you can run a mock OpenAI-compatible server (see `mock_llm_server.py` if present, or create a simple Flask endpoint at `/v1/chat/completions`).
