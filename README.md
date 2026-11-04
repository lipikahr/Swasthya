# Swasthya

Swasthya is an agentic nutrition tracker. People record what they eat in natural language. Nutrition facts come from a verified dataset, and the calculations are deterministic.

## Stack

- Django and Django REST Framework
- PostgreSQL with pgvector
- React and TypeScript (Vite)
- LangGraph, with a replaceable model provider

## Prerequisites

Install these before you clone and run the app:

| Tool | Notes |
| --- | --- |
| [Git](https://git-scm.com/) | Clone the repository |
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | Runs PostgreSQL (pgvector) and Redis |
| [Python 3.12+](https://www.python.org/downloads/) | Backend; tick “Add Python to PATH” on Windows |
| [Node.js 20+](https://nodejs.org/) | Frontend (includes `npm`) |

Optional for full Coach features:

- [OpenRouter](https://openrouter.ai/keys) or [Gemini](https://aistudio.google.com/) API key for chat
- [Sarvam](https://dashboard.sarvam.ai) API key for speech-to-text

## Clone the repository

```powershell
git clone <repository-url> Swasthya
cd Swasthya
```

Replace `<repository-url>` with the Git remote you were given.

## 1. Create the root `.env`

Docker Compose and Django both read **one** file: the repository root `.env` (same folder as `docker-compose.yml`).

```powershell
copy .env.example .env
```

On macOS or Linux:

```bash
cp .env.example .env
```

Open `.env` and set at least:

- `DJANGO_SECRET_KEY` — a long random string
- `POSTGRES_PASSWORD` — letters, digits, `-`, `_`, `.`, or `~` only (no `@ : / # % ?`)
- `DATABASE_URL` — must use the **same** user, password, and database name as `POSTGRES_*`, with host `localhost` and port **5433**

Example shape (change the password in both places):

```env
POSTGRES_DB=nutrition
POSTGRES_USER=nutrition
POSTGRES_PASSWORD=your-safe-password
DATABASE_URL=postgres://nutrition:your-safe-password@localhost:5433/nutrition
```

Leave `OPENROUTER_API_KEY`, `GEMINI_API_KEY`, and `SARVAM_API_KEY` empty until you have keys. The app still runs; chat and voice use limited or unavailable modes without them.

**Never commit `.env`.**

## 2. Start PostgreSQL and Redis

Start Docker Desktop, then from the repository root:

```powershell
docker compose up -d db redis
```

Check that the database is healthy:

```powershell
docker compose ps
```

Notes:

- Host port **5433** maps to Postgres inside Docker (so it does not clash with a local Postgres on 5432).
- Inside Compose the database host is still `db` on port 5432.
- Do **not** run `docker compose down -v` unless you intend to wipe the database volume.

## 3. Set up the backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

On macOS or Linux:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Apply migrations:

```powershell
python manage.py migrate
```

### Load the nutrition dataset (first time)

The verified Anuvaad workbook is **not** in Git (`data/raw/` is ignored). Place this file before the first load:

```text
data/raw/Anuvaad_INDB_2024.11.xlsx
```

(relative to the repository root, not `backend/`)

Then from `backend/`:

```powershell
python manage.py load_nutrition
python manage.py load_embeddings
```

You only need these again after a fresh database (for example after a volume wipe).

Create an account in the UI after the frontend is up, or create a Django user:

```powershell
python manage.py createsuperuser
```

Start the API:

```powershell
python manage.py runserver
```

| URL | Purpose |
| --- | --- |
| http://127.0.0.1:8000/ | API root |
| http://127.0.0.1:8000/api/health/ | Health check |
| http://127.0.0.1:8000/api/docs/ | API docs |

Leave this terminal open while you develop.

## 4. Set up the frontend

Open a **second** terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open **http://127.0.0.1:5173/** in the browser. Vite proxies `/api` to the Django server on port 8000, so both processes must be running.

## Day-to-day restart

After the first setup, a normal session is:

```powershell
# Terminal 1 — from repository root
docker compose up -d db redis

# Terminal 2 — backend
cd backend
.\.venv\Scripts\Activate.ps1
python manage.py runserver

# Terminal 3 — frontend
cd frontend
npm run dev
```

On macOS or Linux, activate the venv with `source .venv/bin/activate` instead.

## Stopping services

- Stop Django and Vite with `Ctrl+C` in their terminals.
- Stop containers without deleting data:

```powershell
docker compose stop
```

- Avoid `docker compose down -v` unless you want to reset Postgres data.

## Optional API keys

Edit the root `.env`, then restart `runserver`:

| Variable | Used for |
| --- | --- |
| `OPENROUTER_API_KEY` | Live Coach chat (preferred when set) |
| `GEMINI_API_KEY` | Alternate text model if OpenRouter is empty |
| `SARVAM_API_KEY` | Voice input / TTS in Coach |

Keys stay on the server only. Do not put them in frontend code or commit them.

## Troubleshooting

| Problem | What to check |
| --- | --- |
| `connect ECONNREFUSED 127.0.0.1:8000` in Vite | Backend is not running; start `manage.py runserver` |
| Database connection errors | Docker is running; `docker compose ps` shows `db` healthy; `.env` `DATABASE_URL` uses port **5433** |
| `load_nutrition` fails | Workbook path `data/raw/Anuvaad_INDB_2024.11.xlsx` exists |
| Port 5433 already in use | Another Compose project may own it; stop that stack or change the published port in `docker-compose.yml` and matching `DATABASE_URL` |
| Password / URL errors for Postgres | Password must be URI-safe; keep `POSTGRES_*` and `DATABASE_URL` in sync |

## What not to commit

- `.env` and any real API keys
- `data/raw/` (nutrition workbook)
- `backend/.venv/`, `frontend/node_modules/`, build output
