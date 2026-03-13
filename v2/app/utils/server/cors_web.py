"""
CORS configuration utility for the FastAPI server.
"""

from __future__ import annotations

from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI

def enable_cors(app: FastAPI):
    """Enable CORS for the given FastAPI app."""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    print("CORS enabled for all origins (FastAPI).")
