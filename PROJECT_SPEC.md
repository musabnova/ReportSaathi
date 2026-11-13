# ReportSaathi - Medical Report Explainer

## PROJECT
ReportSaathi - a plain-language medical report explainer.
Users upload a photo/PDF of a lab report (or paste text). The app extracts the text and returns a simple explanation: what each test is, whether the value is normal/high/low, what it might mean in everyday words, and questions to ask a doctor.

## STACK
- **backend/**: Python 3.11+, FastAPI, pytesseract (Tesseract OCR), google-generativeai or google-genai SDK for Gemini, supabase-py. Config only via environment variables.
- **frontend/**: React + Vite, simple mobile-friendly UI.
- **Database**: Supabase (Postgres).
- **Deploy**: backend on Render (Docker), frontend on Cloudflare Pages.
- **Telegram bot**: uses the same backend.

## RULES
- Never hard-code secrets. Use .env locally and provide .env.example.
- .gitignore must exclude .env, node_modules, __pycache__, venv.
- Always show a medical disclaimer: this is educational, not a diagnosis.
- Never claim a diagnosis or recommend medicines/doses.
- Keep code simple and commented so beginners can follow it.
- Add a README with run instructions.

