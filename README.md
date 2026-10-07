# Renewable Energy Project Automation Analysis System

Full-stack app: **FastAPI** backend, **React (Vite)** frontend, **MySQL** database.

```
backend/    FastAPI + SQLAlchemy (PyMySQL driver)
frontend/   React + Vite (proxies /api to the backend in dev)
docker-compose.yml   MySQL 8.4 container
```

## 1. Database (MySQL)

Option A — Docker:

```bash
docker compose up -d
```

Option B — Homebrew:

```bash
brew install mysql
brew services start mysql
mysql -u root < backend/db/init.sql
```

Both create database `automation_process` with user `app_user` / `app_password`.
Tables are created automatically when the backend starts.

## 2. Backend (FastAPI)

```bash
cd backend
cp .env.example .env          # adjust DB credentials if needed
../.venv/bin/pip install -r requirements.txt
../.venv/bin/uvicorn app.main:app --reload
```

- API: http://127.0.0.1:8000/api
- Swagger docs: http://127.0.0.1:8000/docs
- Health check (incl. DB): http://127.0.0.1:8000/api/health

### Endpoints

| Method | Path                    | Description      |
| ------ | ----------------------- | ---------------- |
| GET    | `/api/projects`         | List projects    |
| POST   | `/api/projects`         | Create project   |
| GET    | `/api/projects/{id}`    | Get one project  |
| PATCH  | `/api/projects/{id}`    | Update project   |
| DELETE | `/api/projects/{id}`    | Delete project   |
| GET    | `/api/projects/{id}/compliance-checks` | List a project's compliance checks |
| POST   | `/api/projects/{id}/compliance-checks` | Add one check or a list of checks |
| GET    | `/api/compliance-checks` | List checks (filter by `project_id`, `status`, `severity`, `rule_code`) |
| GET    | `/api/compliance-checks/{id}` | Get one check |
| DELETE | `/api/compliance-checks/{id}` | Delete check |

## 3. Frontend (React)

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

## 4. Main Page
<img width="1069" height="344" alt="SPAAS Main Page" src="https://github.com/user-attachments/assets/fca382b1-5940-4f02-b4c7-c41f6bd6e9ed" />


## 5. Extract File and show the cleaned data
<img width="1059" height="738" alt="SPAAS ExtractFiles" src="https://github.com/user-attachments/assets/33cabe36-f7b3-4d81-9ea1-b9adf5ccfd20" />

<img width="1064" height="672" alt="SPAAS DataTable" src="https://github.com/user-attachments/assets/ba736e5d-76d3-4bc7-a4b9-80c1a9e9d9fd" />

## 6. Data Dashboard
<img width="947" height="769" alt="SPAAS DataDashbord" src="https://github.com/user-attachments/assets/1f23fd86-cf82-4d0f-bb4c-505e2656b658" />






