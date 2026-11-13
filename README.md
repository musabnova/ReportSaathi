# ReportSaathi

> **Medical Disclaimer**: ReportSaathi is an educational tool designed to help users understand common lab test terminology in plain language. It does **not** provide medical advice, diagnosis, or treatment recommendations. Always consult a qualified physician or healthcare provider regarding any lab results or medical symptoms.

---

## Project Structure

```text
ReportSaathi/
├── PROJECT_SPEC.md     # Project specification and rules
├── README.md           # Getting started guide
├── .gitignore          # Git exclusion rules
├── backend/            # FastAPI backend service
│   ├── main.py         # Application entry point & health check
│   ├── requirements.txt# Backend Python dependencies
│   └── .env.example    # Environment variable template
└── frontend/           # React + Vite frontend (coming soon)
```

---

## Backend Setup & Run Instructions

Follow the steps below to set up a Python virtual environment and run the backend locally.

### 1. Prerequisites
- Python 3.11 or higher installed on your system.
- Tesseract OCR installed on your system (for future OCR extraction).

### 2. Open Terminal in the Project Root
Navigate to the project root directory:
```bash
cd c:\Users\musab\OneDrive\Desktop\ReportSaathi
```

### 3. Create a Python Virtual Environment
Navigate to `backend` and create a virtual environment named `venv`:

**On Windows (PowerShell):**
```powershell
cd backend
python -m venv venv
```

**On macOS / Linux:**
```bash
cd backend
python3 -m venv venv
```

### 4. Activate the Virtual Environment

**On Windows (PowerShell):**
```powershell
.\venv\Scripts\Activate.ps1
```
*(If you encounter execution policy restrictions on PowerShell, run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` once).*

**On Windows (Command Prompt - CMD):**
```cmd
venv\Scripts\activate.bat
```

**On macOS / Linux:**
```bash
source venv/bin/activate
```

### 5. Install Dependencies
With the virtual environment activated, install the required packages:
```bash
pip install -r requirements.txt
```

### 6. Configure Environment Variables
Copy the `.env.example` file to `.env`:

**On Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
```

**On Linux / macOS:**
```bash
cp .env.example .env
```

Fill in your actual API keys and credentials in `.env` (never commit this file to git).

### 7. Run the Backend Server
Start the FastAPI server using Uvicorn with auto-reload enabled:
```bash
uvicorn main:app --reload --port 8000
```

### 8. Verify the Setup
Once running, verify the backend by opening:
- Health check: [http://localhost:8000/health](http://localhost:8000/health) (Expected output: `{"status": "ok"}`)
- Root endpoint: [http://localhost:8000/](http://localhost:8000/)
- Interactive API docs (Swagger UI): [http://localhost:8000/docs](http://localhost:8000/docs)

