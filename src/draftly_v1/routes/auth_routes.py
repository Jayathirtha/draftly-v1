"""Authentication and OAuth routes"""
import logging
from draftly_v1.services.utils.session_mangement import create_user_session
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import Flow
from draftly_v1.services.database import store_user
from draftly_v1.config import CLIENT_SECRETS_FILE, GMAIL_SCOPES, REDIRECT_URI

_logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/me")
async def get_current_user(request: Request):
    """Get current authenticated user from cookie"""
    user_email = request.cookies.get("user_email")
    if not user_email:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"email": user_email, "authenticated": True}


@router.post("/logout")
async def logout(request: Request):
    """Logout and clear session"""
    from fastapi.responses import JSONResponse
    response = JSONResponse(content={"message": "Logged out successfully"})
    response.delete_cookie("user_email")
    response.delete_cookie("session_token")
    return response


@router.get("/login")
async def login():
    """Initiate OAuth login flow"""
    try:
        if not CLIENT_SECRETS_FILE.exists():
            raise HTTPException(
                status_code=500,
                detail=f"Client secrets file not found at: {CLIENT_SECRETS_FILE}"
            )
        
        flow = Flow.from_client_secrets_file(
            str(CLIENT_SECRETS_FILE),
            scopes=GMAIL_SCOPES,
            redirect_uri=REDIRECT_URI
        )
        authorization_url, state = flow.authorization_url(
            access_type='offline', 
            include_granted_scopes='true'
        )
        return RedirectResponse(authorization_url)
    except Exception as e:
        _logger.error(f"Error in login: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Authentication error: {str(e)}")


@router.get("/callback")
async def auth_callback(request: Request):
    """OAuth callback endpoint"""
    try:
        flow = Flow.from_client_secrets_file(
            str(CLIENT_SECRETS_FILE),
            scopes=GMAIL_SCOPES,
            redirect_uri=REDIRECT_URI
        )
        flow.fetch_token(authorization_response=str(request.url))
        
        credentials = flow.credentials
        user_info_service = build('oauth2', 'v2', credentials=credentials)
        user_info = user_info_service.userinfo().get().execute()
        user_email = user_info.get("email")
        
        store_user(
            email=user_email,
            refresh_token=credentials.token,
            style_profile=None
        )
        token = create_user_session(user_email=user_email)
        # Redirect to home without email in URL
        response = RedirectResponse(url='http://localhost:8000/home', status_code=302)
        # Set secure cookie with email (httpOnly for security)
        response.set_cookie(
            key="user_email",
            value=user_email,
            max_age=3600 * 24,  # 24 hours
            httponly=True,
            secure=False,  
            samesite='lax',
        )
        response.set_cookie(    
            key="session_token",
            value=token,
            max_age=3600 * 24,  # 24 hours
            httponly=True,
            secure=False, 
            samesite='lax',
        )
        return response
    except Exception as e:
        _logger.error(f"Error in callback: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Callback error: {str(e)}")
