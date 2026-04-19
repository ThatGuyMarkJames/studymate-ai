# StudyMate AI — Complete Setup Guide

## Prerequisites
- Python 3.10+
- MySQL 8.0+
- Git

---

## 1. Clone / Extract Project

```bash
# If using git
git clone <your-repo-url> studymate
cd studymate

# Or just navigate to the extracted folder
cd studymate
```

---

## 2. MySQL Setup

```sql
-- Open MySQL CLI
mysql -u root -p

-- Run the schema
SOURCE database/schema.sql;

-- Verify
SHOW TABLES IN studymate_db;
EXIT;
```

---

## 3. Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt
```

---

## 4. Environment Variables

```bash
# Copy the example file
cp .env.example .env

# Edit .env with your values
```

Your `.env` file:
```
GROQ_API_KEY=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
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_root_password
DB_NAME=studymate_db
SECRET_KEY=studymate-super-secret-key-2024-change-in-prod
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
APP_HOST=0.0.0.0
APP_PORT=8000
UPLOAD_DIR=uploads
MAX_FILE_SIZE_MB=10
```

---

## 5. Create Uploads Directory

```bash
mkdir -p uploads/vectors
```

---

## 6. Run the Application

```bash
# From the project root (studymate/)
python -m backend.main

# OR using uvicorn directly
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Expected output:
```
Loading embedding model (one-time)...
Embedding model ready.
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

---

## 7. Open in Browser

```
http://localhost:8000
```

API Docs (Swagger):
```
http://localhost:8000/api/docs
```

---

## Project Structure

```
studymate/
├── backend/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app entry point
│   ├── models/
│   │   ├── database.py          # SQLAlchemy ORM models
│   │   └── schemas.py           # Pydantic request/response schemas
│   ├── routers/
│   │   ├── auth.py              # Signup, Login, /me
│   │   ├── study.py             # Subjects, Documents, Chat
│   │   ├── quiz.py              # Quiz generation and submission
│   │   └── dsa.py               # DSA chat + gamification
│   ├── services/
│   │   ├── rag_service.py       # RAG pipeline (chunks, FAISS, retrieval)
│   │   └── llm_service.py       # All Groq LLM calls
│   ├── utils/
│   │   └── auth.py              # JWT + bcrypt utilities
│   └── requirements.txt
├── frontend/
│   ├── index.html               # SPA entry point
│   ├── css/
│   │   └── main.css             # Complete stylesheet
│   └── js/
│       ├── api.js               # All API calls
│       └── app.js               # Full UI logic
├── database/
│   └── schema.sql               # MySQL schema
├── uploads/                     # Created at runtime
│   └── vectors/                 # FAISS indexes
├── .env                         # Your config (not committed)
├── .env.example                 # Template
└── SETUP.md                     # This file
```

---

## API Reference (Key Endpoints)

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/signup` | Register new user |
| POST | `/api/auth/login`  | Login, get JWT |
| GET  | `/api/auth/me`     | Current user info |

### Study Chat
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET    | `/api/study/subjects` | List subjects |
| POST   | `/api/study/subjects` | Create subject |
| POST   | `/api/study/subjects/{id}/documents` | Upload PDF/TXT |
| POST   | `/api/study/chat`     | RAG chat message |
| GET    | `/api/study/chat/{subject_id}/history` | Chat history |

### Quiz
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/quiz/generate` | Generate quiz from docs |
| POST | `/api/quiz/submit`   | Submit answers, get score |
| GET  | `/api/quiz/stats`    | User quiz statistics |

### DSA Practice
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/dsa/chat`             | DSA chatbot message |
| GET  | `/api/dsa/progress`         | XP, level, streak |
| GET  | `/api/dsa/challenge/active` | Today's challenge |
| POST | `/api/dsa/challenge/new`    | Generate new challenge |

---

## Troubleshooting

**MySQL connection refused:**
```bash
# Check MySQL is running
sudo systemctl start mysql   # Linux
brew services start mysql    # Mac
```

**Embedding model download (first run):**
The `all-MiniLM-L6-v2` model (~90MB) downloads automatically on first launch. Requires internet.

**Port already in use:**
```bash
# Change port in .env
APP_PORT=8001
```

**FAISS not installing:**
```bash
pip install faiss-cpu==1.8.0 --no-cache-dir
```
