from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(title="Vehicle C2 Node")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(__file__)

templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "../frontend/templates"))

app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "../frontend/static")), name="static")


@app.get("/")
async def index(request: Request):
    # Serve the frontend index.html directly to avoid Jinja2 caching issues in some environments.
    return FileResponse(os.path.join(BASE_DIR, "../frontend/templates/index.html"))

# Routers (imported lazily to avoid circular imports during scaffold)
try:
    from .routers import radio, sdr, tak, system, websocket
    app.include_router(radio.router)
    app.include_router(sdr.router)
    app.include_router(tak.router)
    app.include_router(system.router)
    app.include_router(websocket.router)
except Exception:
    # in initial scaffold these modules may be missing; ignore import errors
    pass
