import os
import sys
import logging
from contextlib import asynccontextmanager

# Ensure workspace root is in sys.path
workspace_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if workspace_root not in sys.path:
    sys.path.insert(0, workspace_root)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse
from backend.app.core.config import settings
from backend.app.core.init_app import initialize_system
from backend.app.api import api_router


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("crowd_safety")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing system schemas, credentials, and video assets...")
    initialize_system()
    logger.info(f"{settings.APP_NAME} started successfully.")
    yield
    logger.info("Application shutting down.")

app = FastAPI(
    title=settings.APP_NAME,
    description="Backend API for AI-Powered Intelligent Crowd Management and Public Safety Monitoring System",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Router under /api
app.include_router(api_router, prefix=settings.API_V1_STR)

# Serve Frontend static assets and HTML files directly from FastAPI for seamless single-command demo
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
frontend_dir = os.path.join(project_root, "frontend")

if os.path.exists(frontend_dir):
    # Mount sub-directories for relative assets (css/, js/, assets/)
    css_dir = os.path.join(frontend_dir, "css")
    js_dir = os.path.join(frontend_dir, "js")
    assets_dir = os.path.join(frontend_dir, "assets")

    if os.path.exists(css_dir):
        app.mount("/css", StaticFiles(directory=css_dir), name="css")
    if os.path.exists(js_dir):
        app.mount("/js", StaticFiles(directory=js_dir), name="js")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    # Serve HTML pages directly at root
    @app.get("/")
    def index():
        return FileResponse(os.path.join(frontend_dir, "index.html"))

    @app.get("/login.html")
    def login_page():
        return FileResponse(os.path.join(frontend_dir, "login.html"))

    @app.get("/dashboard.html")
    def dashboard_page():
        return FileResponse(os.path.join(frontend_dir, "dashboard.html"))

    @app.get("/cameras.html")
    def cameras_page():
        return FileResponse(os.path.join(frontend_dir, "cameras.html"))

    @app.get("/live-monitoring.html")
    def live_monitoring_page():
        return FileResponse(os.path.join(frontend_dir, "live-monitoring.html"))

    @app.get("/settings.html")
    def settings_page():
        return FileResponse(os.path.join(frontend_dir, "settings.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
