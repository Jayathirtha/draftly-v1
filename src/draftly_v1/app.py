import sys
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from google_auth_oauthlib.flow import Flow
from dotenv import load_dotenv
import logging
import os
# Allow insecure transport for local development ONLY
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

load_dotenv()

app = FastAPI()

_logger = logging.getLogger(__name__)

# Scopes required for Draftly
SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',  # To create drafts
    'https://www.googleapis.com/auth/gmail.readonly' # To read messages for style learning
]

# Path to your client_secret.json downloaded from Google Console
# Get the project root directory (three levels up from this file: app.py -> draftly_v1 -> src -> draftly-v1)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CLIENT_SECRETS_FILE = BASE_DIR / "resources" / "client_secret_695824097654-6bmqmtgpd8t23tkve76kvmje9u0fga9f.apps.googleusercontent.com.json"

@app.get("/")
async def root():
    """Root endpoint to verify the app is running"""
    return {"message": "Draftly API is running", "endpoints": ["/auth/login", "/auth/callback"]}

@app.get("/auth/login")
async def login():
    """Initiate OAuth login flow"""
    try:
        # Check if client secrets file exists
        if not CLIENT_SECRETS_FILE.exists():
            raise HTTPException(
                status_code=500,
                detail=f"Client secrets file not found at: {CLIENT_SECRETS_FILE}"
            )
        
        # Initialize the OAuth flow
        flow = Flow.from_client_secrets_file(
            str(CLIENT_SECRETS_FILE),
            scopes=SCOPES,
            redirect_uri='http://localhost:8000/auth/callback'
        )
        authorization_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true')
        return RedirectResponse(authorization_url)
    except Exception as e:
        _logger.error(f"Error in login: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Authentication error: {str(e)}")

@app.get("/auth/callback")
async def auth_callback(request: Request):
    """OAuth callback endpoint"""
    try:
        # Exchange authorization code for tokens
        flow = Flow.from_client_secrets_file(
            str(CLIENT_SECRETS_FILE),
            scopes=SCOPES,
            redirect_uri='http://localhost:8000/auth/callback'
        )
        flow.fetch_token(authorization_response=str(request.url))
        
        credentials = flow.credentials
        # Save these credentials (especially the refresh_token) to your DB
        return {
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "expires_at": credentials.expiry.isoformat() if credentials.expiry else None
        }
    except Exception as e:
        _logger.error(f"Error in callback: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Callback error: {str(e)}")



def setup_logging(loglevel):
    """Setup basic logging

    Args:
      loglevel (int): minimum loglevel for emitting messages
    """
    logformat = "[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
    logging.basicConfig(
        level=loglevel, stream=sys.stdout, format=logformat, datefmt="%Y-%m-%d %H:%M:%S"
    )


def main():
    """Start the FastAPI application using uvicorn"""
    import uvicorn
    setup_logging(logging.INFO)
    _logger.info("Starting Draftly application...")
    _logger.info(f"Client secrets file path: {CLIENT_SECRETS_FILE}")
    _logger.info(f"Client secrets file exists: {CLIENT_SECRETS_FILE.exists()}")
    
    # Run the server
    uvicorn.run(
        "draftly_v1.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )


def run():
    """Calls :func:`main` passing the CLI arguments extracted from :obj:`sys.argv`

    This function can be used as entry point to create console scripts with setuptools.
    """
    main()


if __name__ == "__main__":
    # ^  This is a guard statement that will prevent the following code from
    #    being executed in the case someone imports this file instead of
    #    executing it as a script.
    #    https://docs.python.org/3/library/__main__.html

    # After installing your project with pip, users can also run your Python
    # modules as scripts via the ``-m`` flag, as defined in PEP 338::
    #
    #     python -m draftly_v1.app
    #
    run()
