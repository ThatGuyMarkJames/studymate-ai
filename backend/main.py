import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

from backend.models.database import Base, engine
from backend.routers import auth, study, quiz, dsa
from backend.routers import flashcards, notes

load_dotenv()

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title       = "StudyMate AI",
    description = "Intelligent study assistant platform for college students",
    version     = "1.1.0",
    docs_url    = "/api/docs",
    redoc_url   = "/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

app.include_router(auth.router,       prefix="/api")
app.include_router(study.router,      prefix="/api")
app.include_router(quiz.router,       prefix="/api")
app.include_router(dsa.router,        prefix="/api")
app.include_router(flashcards.router, prefix="/api")
app.include_router(notes.router,      prefix="/api")

frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

    @app.get("/")
    def serve_index():
        return FileResponse(str(frontend_dir / "index.html"))

    @app.get("/{path:path}")
    def serve_spa(path: str):
        file_path = frontend_dir / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(frontend_dir / "index.html"))


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "StudyMate AI"}


if __name__ == "__main__":
    import uvicorn
    # Railway provides the port via the PORT environment variable
    port = int(os.getenv("PORT") or os.getenv("APP_PORT") or 8000)
    
    uvicorn.run(
        "backend.main:app",
        host    = os.getenv("APP_HOST", "0.0.0.0"),
        port    = port,
        reload  = False,  # Disable reload in production
        workers = 1,
    )

