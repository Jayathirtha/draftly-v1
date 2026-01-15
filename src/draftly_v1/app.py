"""Draftly - AI Email Assistant Application"""
import sys
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from draftly_v1.services.utils.logger_config import setup_logging
from draftly_v1.config import FRONTEND_DIR, ALLOWED_ORIGINS
from draftly_v1.routes import auth_routes, email_routes, static_routes

# Setup logging
setup_logging(logging.INFO)
_logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Draftly API",
    description="AI-powered email drafting assistant",
    version="1.0.0"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/ui", StaticFiles(directory=FRONTEND_DIR, html=True), name="ui")

# Include routers
app.include_router(static_routes.router)
# Include routers
app.include_router(static_routes.router)
app.include_router(auth_routes.router)
app.include_router(email_routes.router)


def main():
    """Start the FastAPI application using uvicorn"""
    import uvicorn
    from draftly_v1.config import CLIENT_SECRETS_FILE
    
    _logger.info("Starting Draftly application...")
    _logger.info(f"Client secrets file exists: {CLIENT_SECRETS_FILE.exists()}")
    
    uvicorn.run(
        "draftly_v1.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )


def run():
    """Entry point for console scripts"""
    main()


if __name__ == "__main__":
    run()

