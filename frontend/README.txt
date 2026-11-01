Sahayak OCR Candidate Review Fix (v1)
===================================== 

ISSUE
The DocAI bridge excludes uncertain fields from legacy top-level values in order
to avoid automatic false matches. The original Checklist UI only looks at those
legacy values and incorrectly says OCR could not read anything.

FRONTEND FIX (from the folder containing package.json)
  node .\fix_ocr_review.cjs
  npm.cmd run build
  npm.cmd run dev -- --port 5173 --strictPort

This shows unconfirmed OCR candidates in the UI, and allows users to review/edit
and save them explicitly. No automatic DB verification is added.

BACKEND DIAGNOSTIC (from the backend folder)
  Copy ocr_health_check.py into the backend root (beside app.py).
  .\venv\Scripts\python.exe .\ocr_health_check.py

Optional, with a locally stored sample and document-type hint:
  .\venv\Scripts\python.exe .\ocr_health_check.py "C:\private\test-image.jpg" aadhaar

Only flags and field-presence information are printed, not actual document data.

ROLLBACK
Delete the modified Checklist.jsx and rename the timestamped .bak file
created by the installer to Checklist.jsx. OCR backend opt-in can be disabled
by removing SMARTAPPLY_DOC_AI=1 from the backend process environment and restarting.

LIMITATIONS
This fixes a UI/adapter mismatch. It does not increase OCR recognition accuracy
or solve missing Tesseract binaries, low-quality images, unsupported layouts.
Do not claim 98% accuracy without real consented fixtures and held-out benchmarks.
