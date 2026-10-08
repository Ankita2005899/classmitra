# Phase 0: setup, REST, secrets (about 3 days)

## Goal
Run a small API on your computer, call it from the browser, test it, and keep a secret out of Git.

## Run it (Windows PowerShell, from the project root)
```
cd backend
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```
If PowerShell blocks the activate script, run once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

Open http://127.0.0.1:8000/docs. This page lists every endpoint and lets you try them.

Run the tests (new terminal tab, venv active, inside `backend`): `pytest`

## Concepts

**REST API.** The server exposes *resources* (departments, lessons) at URLs. You act on them with *verbs*:

| Verb | Meaning | Example |
|---|---|---|
| GET | read | GET /api/departments |
| POST | create | POST /api/lessons |
| PUT / PATCH | change | PATCH /api/lessons/5 |
| DELETE | remove | DELETE /api/lessons/5 |

The reply has a **status code**: 200 OK, 201 Created, 400 bad request, 401 not logged in, 403 not allowed, 404 not found, 500 server error. Data travels as **JSON**.

**Environment variables and `.env`.** A secret in code gets copied with the code. So the code reads it from the environment (`config.py`), and on your machine the value sits in `backend/.env`, which Git ignores. `.env.example` is committed so others know which keys exist, with the values left empty.

**Why keys never go in JavaScript.** Anyone can open the browser's developer tools and read your JS. A key there is public. The browser calls *your* backend, and the backend calls the paid or keyed service.

**CORS.** Browsers block a website from calling a different address unless that server allows it. `allowed_origins` is that allow-list.

## Exercises
1. In /docs, call GET /api/departments, then GET /api/departments/comp, then /api/departments/xyz. Note each status code.
2. Add `GET /api/health/time` that returns the current time. Write a test for it.
3. Put a fake value in `.env` as GEMINI_API_KEY, restart, and open /api/config-check. Confirm it shows true but never the value.
4. Run `git check-ignore -v backend/.env`.

## Check yourself (answer in your own words)
1. What is the difference between GET and POST?
2. Why does /api/config-check return only true or false?
3. What happens if a key is committed by mistake, and what do you do?
4. Why does the browser need CORS but the tests don't?
5. What does `--reload` do, and why not use it in production?
