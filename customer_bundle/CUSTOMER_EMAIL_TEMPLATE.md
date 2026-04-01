Subject: SIPMT customer delivery package and installation steps

Hello,

Attached is the SIPMT delivery package for your installation.

The package includes:

- the SIPMT application container
- a bundled PostgreSQL database container
- a bundled Ollama container with the required model
- startup, validation, backup, and restore scripts

Please install Docker Desktop first if it is not already available on the target machine.

After extracting the delivery package, open a terminal in the package folder and run:

```bash
docker load -i images/incluscape-sipmt.tar
docker load -i images/incluscape-ollama.tar
docker load -i images/postgres-16-alpine.tar

docker compose up -d postgres ollama sipmt
bash scripts/smoke_test_bundle.sh
```

If the smoke test passes, open the application at:

`http://localhost:8501`

Before first startup, please review the `.env` file and replace these values:

- `POSTGRES_PASSWORD`
- `SECRET_KEY`

If your environment also uses Gemini, add your `GEMINI_API_KEY` to `.env`.

Useful operations after installation:

- check status: `docker compose ps`
- view logs: `docker compose logs -f sipmt ollama postgres`
- stop services: `docker compose down`
- create backup: `bash scripts/backup_customer_data.sh`
- restore backup: `bash scripts/restore_customer_data.sh <backup-directory>`

Important:

- do not run `docker compose down -v` unless you intentionally want to remove stored customer data
- keep the `images/` folder so the bundle can be re-imported on another machine if needed

Please confirm once the smoke test passes on your side.

Regards,

Branislav