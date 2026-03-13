from __future__ import annotations

import uvicorn
from fastapi import FastAPI
import asyncio
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from v2.app.api.api_router import api_router
from v2.app.utils.server.ssl_cert import get_ssl_args_for_uvicorn
from v2.app.utils.server.cors_web import enable_cors

app = FastAPI(
    title="Smart Glasses Gateway",
    description="Modular Gateway for Multi-Agent Image Analysis",
    version="2.0.0"
)

enable_cors(app)
app.include_router(api_router)


@app.on_event("startup")
async def _init_state_asyncio_primitives():
    from v2.app import state
    state.init_async_primitives()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Invalid request body. Use JSON for /tools/* or form-data with 'image' for /mobile/process.",
            "errors": [{"loc": err.get("loc"), "msg": err.get("msg")} for err in exc.errors()],
        },
    )


def run_server(host: str = "0.0.0.0", port: int = 5050, ssl: bool = False):
    print(f"Starting Gateway Server on {host}:{port}...")
    config = {"app": app, "host": host, "port": port, "log_level": "info"}
    if ssl:
        ssl_args = get_ssl_args_for_uvicorn()
        if ssl_args:
            config.update(ssl_args)
            print("SSL enabled.")
        else:
            print("SSL requested but certificates not found. Running without SSL.")
    uvicorn.run(**config)


if __name__ == "__main__":
    run_server()
