# Vercel frontend + Render backend

This setup deploys a fresh database. It does not upload local accounts, identity documents, encryption keys or `.env` files.

## Render

Import this repository as a Blueprint using root `render.yaml`. It selects a **free** single-instance Docker service in Singapore, without any paid disk or database. Both PaddleOCR and Tesseract are included. Free-tier RAM/CPU may be insufficient for Paddle; an actual synthetic upload must pass before this can be called a working OCR deployment. Do not upgrade to a paid service automatically.

Free Render services sleep after inactivity. Accounts and uploads are ephemeral and reset on restarts/redeploys. This is a synthetic-data demo, not a production identity-document service.
Set `FRONTEND_ORIGIN` and `CORS_ORIGINS` to the exact stable Vercel HTTPS origin (no trailing slash). Render generates separate new `SECRET_KEY` and `IDENTITY_ENCRYPTION_KEY` values. Back up those securely and never regenerate them for an existing database. Docker installs English Tesseract and downloads Paddle's English mobile models during the image build. The first image build can take several minutes.

SQLite lives at `/tmp/sahayak-demo/sahayak.db`, documents at `/tmp/sahayak-demo/uploads`. They do **not** survive service restarts. Extracted Aadhaar/PAN numbers remain encrypted, but original uploads and other profile fields are not encrypted by the app. Do not upload real personal documents to this public free demo. Do not scale beyond one instance or one Gunicorn worker: the bounded OCR queue and cache are process-local. A persistent launch needs storage and an external queue before multi-instance scaling.
Gunicorn uses one process and four request threads, while one OCR worker processes queued jobs. `/api/health` checks HTTP availability; `/api/ocr/health` separately reports model readiness. Do not announce OCR ready until its `ready` value is true.

## Vercel

Import this repository, choose root directory `frontend`, and enable **Include source files outside of the Root Directory in the Build Step** (extension sources are in the sibling directory). Select Node 22.x. `frontend/vercel.json` supplies the build command and uses Vercel Build Output API.

Set these production build environment variables:

- `RENDER_BACKEND_URL`: exact Render HTTPS service origin, without `/api` or a path.
- `SAHAYAK_APP_ORIGIN`: exact stable public frontend HTTPS origin. It is added to the downloadable extension's allowlist. If omitted, the packager can use `VERCEL_PROJECT_PRODUCTION_URL` supplied by Vercel.
- `VITE_DEMO_MODE`: `1` (shows the temporary-data notice on every page).
- Leave `VITE_API_BASE` unset or empty.

The build creates `.vercel/output`, including SPA route handling and an external `/api/*` rewrite to Render. Browser API requests stay on the frontend origin, avoiding third-party cookie dependence. API responses are marked no-store. Do not enable CDN caching for API paths. Preview frontend origins are deliberately not trusted for full-ID transfer; configure explicit staging backends if needed.

After deployment, download the extension ZIP from the live site. Local-only extension copies do not trust a new production domain. Extract the new ZIP and reload/install it via Chrome Developer mode.

## Verify

1. Frontend loads and a direct `/login` navigation renders the app.
2. `/api/health` returns JSON through the frontend URL and `/api/ocr/health` reports ready.
3. Register a synthetic test account, sign out, and sign back in; session cookies are Secure, HttpOnly and SameSite=Lax.
4. Upload synthetic OCR fixtures and poll until completion. Review fields and transfer to the production ZIP extension.
5. Confirm unauthenticated full-ID requests return 401, ordinary reports remain masked, and API responses carry no-store.
6. Verify the free-demo warning is visible. Expect the synthetic account/upload to disappear after a Render restart.

A successful frontend build does not prove the Docker image or OCR service is live. Verify the deployment logs and live endpoints before sharing the URL.
