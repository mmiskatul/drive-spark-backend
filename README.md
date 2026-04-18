# Drive Spark Rent Backend

FastAPI backend scaffolded for MongoDB Atlas with a layered architecture:

- `api`: HTTP routing and request/response boundaries.
- `core`: settings, security, logging, and shared infrastructure.
- `db`: MongoDB connection lifecycle, index setup, and dependencies.
- `models`: database document models.
- `schemas`: Pydantic API contracts.
- `repositories`: persistence access.
- `services`: business use cases.

## Quick Start

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Set `MONGODB_URI` to your MongoDB Atlas connection string in `.env`.
Set `ADMIN_EMAIL`, `ADMIN_PASSWORD`, and `ADMIN_NAME` in `.env` for the admin account that is seeded when the API starts.

This folder is designed to be an independent backend project. You can initialize and push it separately:

```bash
cd backend
git init
git add .
git commit -m "Initial FastAPI backend"
git remote add origin <your-backend-repo-url>
git push -u origin main
```

## Useful Commands

```bash
ruff check .
pytest
python -m app.scripts.seed_admin
uvicorn app.main:app --host 0.0.0.0 --port 8000
docker build -t drive-spark-rent-api .
docker compose up --build
```

If you prefer package metadata installs:

```bash
pip install -e ".[dev]"
```

## API Flow

The current scaffold includes production-ready health endpoints and a cars domain:

- `GET /api/v1/health`
- `GET /api/v1/cars`
- `POST /api/v1/cars`
- `GET /api/v1/cars/{car_id}`
- `PATCH /api/v1/cars/{car_id}`
- `DELETE /api/v1/cars/{car_id}`

OpenAPI docs are available at `/docs` outside production.

## MongoDB Atlas Notes

Use an Atlas URI with an application user that has only the required database permissions. Keep the URI in `.env` or your deployment secret manager; never commit real credentials.
