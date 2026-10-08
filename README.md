# ClassMitra

AI classroom assistant. The dashboard drills down **Department > Class > Division > Subject**, and each subject opens the lesson studio and live classroom.

## Structure

```
index.html, studio.html, css/, js/   Frontend (static, served by GitHub Pages from the repo root)
backend/                             FastAPI server (app/, tests/, requirements.txt, .env.example)
docs/                                DESIGN.md, GIT_WORKFLOW.md, phase-0.md
.github/workflows/ci.yml             Runs the backend tests on every push
```

## Run the frontend

```
python -m http.server 5500
```
Open http://localhost:5500

## Run the backend

See `docs/phase-0.md`. Short version:

```
cd backend
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```
API docs: http://127.0.0.1:8000/docs

## Roadmap

Phase 0 setup (done) > 1 backend and database > 2 PPT pipeline > 3 voice-over video > 4 attendance > 5 doubts (RAG) > 6 attention model > 7 avatar > 8 call-outs > 9 polish.

Keep API keys in `backend/.env`. Never put them in the JavaScript.
