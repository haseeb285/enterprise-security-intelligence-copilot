COMPOSE := docker compose

.PHONY: docker-build docker-infra docker-migrate docker-seed docker-ingest docker-train docker-up docker-down docker-logs docker-clean-demo

docker-build:
	$(COMPOSE) --profile bootstrap build api streamlit train

docker-infra:
	$(COMPOSE) up -d postgres qdrant

docker-migrate:
	$(COMPOSE) --profile bootstrap run --rm migrate

docker-seed:
	$(COMPOSE) --profile bootstrap run --rm seed

docker-ingest:
	$(COMPOSE) --profile bootstrap run --rm ingest

docker-train:
	$(COMPOSE) --profile bootstrap run --rm train

docker-up:
	$(COMPOSE) up -d api streamlit

docker-down:
	$(COMPOSE) down

docker-logs:
	$(COMPOSE) logs -f api streamlit

# Destructive: removes this Compose project's PostgreSQL and Qdrant volumes.
docker-clean-demo:
	$(COMPOSE) down --volumes --remove-orphans
