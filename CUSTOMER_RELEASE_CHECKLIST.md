# SIPMT Customer Release Checklist

## 1. Pre-Install Preparation

- Confirm customer machine has Docker Desktop or Docker Engine + Docker Compose available.
- Confirm outbound internet access is available for runtime features that depend on it:
  - geocoding
  - external reference refresh
  - Gemini, if used
- Confirm enough free disk space exists for:
  - SIPMT app image
  - bundled PostgreSQL volume
  - bundled Ollama image and model
  - customer uploads and exports
- Confirm target port `8501` is available.
- Confirm target port `11434` is acceptable if Ollama API exposure is desired on the host.

## 2. Installation Steps

- Copy the release package to the customer machine.
- Create runtime config:
  - copy `.env.production` to `.env`
  - replace `POSTGRES_PASSWORD`
  - replace `SECRET_KEY`
  - optionally adjust `OLLAMA_MODEL`, `GEMINI_API_KEY`, and logging values
- Start the bundle:

```bash
bash scripts/release_bundle.sh
```

## 3. Post-Install Validation

- Run the smoke test:

```bash
bash scripts/smoke_test_bundle.sh
```

- Open the UI at `http://localhost:8501`.
- Confirm these pages load:
  - Documents
  - Reports
  - Changes
  - Map
  - Compliance
- Confirm Ollama is available through the bundled service.
- Confirm PostgreSQL is healthy and persistent volumes are mounted.

## 4. Functional Verification

- Upload a sample PDF or DOCX document.
- Confirm extraction completes successfully.
- Confirm geocoding works when internet access is available.
- Confirm external reference refresh works.
- Confirm compliance analysis works with bundled Ollama.
- If Gemini is configured, confirm Gemini analysis also works.

## 5. Customer Handover

- Provide customer with:
  - application URL
  - default admin or operating procedure, if applicable
  - location of `.env`
  - location of persisted Docker volumes
  - backup expectations for PostgreSQL and exported files
  - restart instructions
  - stop instructions
  - log inspection instructions

## 6. Operations Commands

Start bundle:

```bash
bash scripts/release_bundle.sh
```

Smoke test:

```bash
bash scripts/smoke_test_bundle.sh
```

View status:

```bash
docker compose ps
```

View logs:

```bash
docker compose logs -f sipmt ollama postgres
```

Stop bundle:

```bash
docker compose down
```

Stop and remove volumes:

```bash
docker compose down -v
```

## 7. Acceptance Sign-Off

- Customer confirms application starts successfully.
- Customer confirms document upload works.
- Customer confirms semantic analysis works.
- Customer confirms internet-enabled features work from their network.
- Customer confirms handover materials were received.