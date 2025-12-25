# Repository Guidelines

## Project Structure & Module Organization
- `backend/src`: FastAPI service, core analysis, perception, evaluation, and API routes.
- `backend/tests`: pytest suites for API, input, and analysis modules.
- `backend/config`: runtime configuration (`config.yaml`) and SOP rules (`sop_rules.yaml`).
- `frontend/src`: Vue 3 + TypeScript UI (views, components, stores, router, styles).
- `frontend/public` and `frontend/src/assets`: static assets and icons.
- `docs`: architecture, development, and deployment references.
- `scripts`: helper scripts for dev startup and self-tests.

## Build, Test, and Development Commands
- Backend run: `python -m src.main` from `backend/` (starts the API app).
- Backend dev server: `python -m uvicorn src.api.app:app --reload` (what `scripts/start_dev.sh` uses).
- Backend quality: `black backend/src`, `isort backend/src`, `mypy backend/src`.
- Backend tests: `pytest` or `pytest tests/test_pose_detector.py` from `backend/`.
- Frontend dev: `npm run dev` from `frontend/`.
- Frontend build: `npm run build` (type-checks with `vue-tsc`).
- Frontend preview: `npm run preview`.
- Full-stack dev: `scripts/start_dev.sh` (expects conda env `cc-sop` and ports 8000/5173 free).

## Coding Style & Naming Conventions
- Python follows PEP 8; format with Black (88 cols) and sort imports with isort per `backend/pyproject.toml`.
- Prefer explicit type hints; mypy is configured with strict options in `backend/pyproject.toml`.
- Tests are named `test_*.py` in `backend/tests`.
- Vue/TypeScript code uses 2-space indentation and single quotes; keep component names in PascalCase (e.g., `ScorePanel.vue`).
- Use the `@/` path alias for frontend imports.

## Testing Guidelines
- Primary backend test runner: `pytest` (configured in `backend/pyproject.toml`).
- Coverage: `pytest --cov=src --cov-report=html`.
- `scripts/test_all.sh` runs a local sanity suite (requires the conda env and dependencies).
- Frontend tests are not wired in `frontend/package.json` yet; add scripts there if you introduce tests.

## Commit & Pull Request Guidelines
- Recent history uses short, free-form (often Chinese) summaries; no consistent format is enforced.
- Preferred format per `docs/DEVELOPMENT_GUIDE.md` is Conventional Commits, e.g., `feat(api): add session websocket`.
- PRs should include a clear summary, linked issue (if any), test results, and UI screenshots for frontend changes.
- Call out config changes to `backend/config/config.yaml` or `backend/config/sop_rules.yaml` explicitly.

## Security & Configuration Tips
- Do not commit secrets; keep database credentials and API keys out of the repo.
- When adding new SOP actions or scenarios, update `backend/config/sop_rules.yaml` and document any new IDs.
