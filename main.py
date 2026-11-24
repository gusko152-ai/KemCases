"""Compatibility entrypoint for the current Render start command.

Render's existing service is configured with:
    uvicorn main:app --host 0.0.0.0 --port $PORT

The actual FastAPI application lives in app/main.py.
"""
from app.main import app

__all__ = ["app"]
