"""Static file serving routes"""
from fastapi import APIRouter
from fastapi.responses import FileResponse
from draftly_v1.config import FRONTEND_DIR

router = APIRouter(tags=["static"])


@router.get("/health")
async def health():
    """Root endpoint to verify the app is running"""
    return {
        "message": "Draftly API is running", 
        "endpoints": ["/auth/login", "/auth/callback", "/email/fetch_latest", "/email/draft"]
    }


@router.get("/login")
async def read_login():
    """Serve login page"""
    return FileResponse(FRONTEND_DIR / "login.html")


@router.get("/home")
async def read_home():
    """Serve home page"""
    return FileResponse(FRONTEND_DIR / "index.html")
