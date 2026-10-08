# Swasthya

Swasthya is an agentic nutrition tracker. People record what they eat in natural language. Nutrition facts come from a verified dataset, and the calculations are deterministic.

## Stack

- Django and Django REST Framework
- PostgreSQL with pgvector
- React and TypeScript
- LangGraph, with a replaceable model provider

## Local development

Copy `.env.example` to `.env` in the repository root. Docker Compose and Django both read that file.

```powershell
docker compose up -d db redis
cd backend
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

The API is at `http://127.0.0.1:8000/`. Health is `GET /api/health/`. API docs are at `/api/docs/`.

Compose publishes PostgreSQL on host port 5433 so it can run beside a local PostgreSQL already using port 5432. Inside Compose the database host remains `db` on port 5432.

Do not commit `.env` or the raw nutrition workbook.
