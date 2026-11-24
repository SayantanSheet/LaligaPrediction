"""Entry point kept for `uvicorn main:app` (Procfile / Dockerfile). The app lives in app/main.py."""
from app.main import app  # noqa: F401

if __name__ == "__main__":
    import os

    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
