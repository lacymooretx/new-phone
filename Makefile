.PHONY: up down restart logs migrate seed test lint fmt health web-dev web-build web-test web-lint tls-cert tls-sip-proxy desktop-dev desktop-build desktop-package test-unit test-integration test-e2e test-all lint-all ci rust-check rust-build rust-docker rust-test

# Start all services
up:
	docker compose up -d

# Stop all services
down:
	docker compose down

# Restart all services
restart:
	docker compose down && docker compose up -d

# Follow logs
logs:
	docker compose logs -f

# Run Alembic migrations (inside api container)
migrate:
	docker compose exec api alembic upgrade head

# Load dev seed data
seed:
	docker compose exec -T postgres psql -U new_phone_admin -d new_phone < db/seed/dev-seed.sql

# Run tests (against running API server)
test:
	uv run python -m pytest api/tests/ -v

# Lint
lint:
	cd api && uv run ruff check src/ tests/

# Format
fmt:
	cd api && uv run ruff format src/ tests/

# Web UI
web-dev:
	cd web && npm run dev

web-build:
	cd web && npm run build

web-test:
	cd web && npm run test

web-lint:
	cd web && npm run lint

# Generate self-signed TLS cert for FreeSWITCH (dev only)
tls-cert:
	mkdir -p freeswitch/tls
	openssl req -x509 -newkey rsa:2048 -keyout freeswitch/tls/key.pem -out freeswitch/tls/cert.pem -days 3650 -nodes -subj "/CN=localhost" -addext "subjectAltName=DNS:localhost,DNS:freeswitch,IP:127.0.0.1"
	cat freeswitch/tls/cert.pem freeswitch/tls/key.pem > freeswitch/tls/agent.pem
	cp freeswitch/tls/cert.pem freeswitch/tls/cafile.pem
	@echo "TLS certs generated in freeswitch/tls/"

# Generate self-signed TLS cert for SIP proxy (dev only)
tls-sip-proxy:
	mkdir -p tls
	openssl req -x509 -newkey rsa:2048 -keyout tls/sip-proxy.key -out tls/sip-proxy.crt -days 3650 -nodes -subj "/CN=${NP_PROVISIONING_SIP_SERVER:-pbx.local}" -addext "subjectAltName=DNS:${NP_PROVISIONING_SIP_SERVER:-pbx.local},DNS:sip-proxy,DNS:localhost,IP:127.0.0.1"
	@echo "SIP proxy TLS certs generated in tls/"

# Generate all TLS certs (dev only)
tls-all: tls-cert tls-sip-proxy

# Desktop (Electron)
desktop-dev:
	cd desktop && npm run dev

desktop-build:
	cd web && npm run build && cd ../desktop && npm run build

desktop-package:
	cd desktop && npm run package:mac

# Health check
health:
	@curl -s http://localhost:8000/api/v1/health | python3 -m json.tool

# Unit tests (API only)
test-unit:
	cd api && uv run pytest tests/unit/ -v

# Integration tests (API only)
test-integration:
	cd api && uv run pytest tests/integration/ -v

# End-to-end tests (Playwright)
test-e2e:
	cd web && npx playwright test

# All tests (API unit + web)
test-all: test-unit web-test

# All linters (API + web)
lint-all: lint web-lint

# --- Rust Services ---

# Check Rust workspace compiles
rust-check:
	cd rust && cargo check --workspace

# Build Rust workspace (release)
rust-build:
	cd rust && cargo build --workspace --release

# Run Rust tests
rust-test:
	cd rust && cargo test --workspace

# Build all Rust service Docker images
RUST_SERVICES := sip-proxy rtp-relay dpma-service event-router parking-manager e911-handler sms-gateway
rust-docker:
	@for svc in $(RUST_SERVICES); do \
		echo "Building newphone/$$svc..."; \
		docker build -f rust/crates/$$svc/Dockerfile -t newphone/$$svc rust/ || exit 1; \
	done
	@echo "All Rust service images built."

# Build a single Rust service Docker image (usage: make rust-docker-one SVC=sip-proxy)
rust-docker-one:
	docker build -f rust/crates/$(SVC)/Dockerfile -t newphone/$(SVC) rust/

# Full CI check (lint + test + build)
ci: lint-all test-all web-build rust-check
