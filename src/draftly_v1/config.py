"""Application configuration and constants"""
import os
from pathlib import Path
from dotenv import load_dotenv
import glob

load_dotenv()

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent

def get_client_secrets_file():
    """Find the first client_secret*.json file in resources directory"""
    resources_dir = BASE_DIR / "resources"
    if not resources_dir.exists():
        raise FileNotFoundError(f"Resources directory not found: {resources_dir}")
    
    # Search for any client_secret*.json file
    secret_files = list(resources_dir.glob("client_secret*.json"))
    
    if not secret_files:
        raise FileNotFoundError(
            f"No client_secret*.json file found in {resources_dir}. "
            "Please download your OAuth credentials from Google Cloud Console."
        )
    
    if len(secret_files) > 1:
        print(f"Warning: Multiple client secret files found. Using: {secret_files[0].name}")
    
    return secret_files[0]

CLIENT_SECRETS_FILE = get_client_secrets_file()
FRONTEND_DIR = BASE_DIR / "frontend"

# OAuth Configuration
GAPI = os.getenv("GAPI")
GMAIL_SCOPES = [
    f"{GAPI}{scope.strip()}" if scope.strip().startswith("auth/") else scope.strip() 
    for scope in os.getenv("GMAIL_SCOPES", "").split(",")
]
REDIRECT_URI = 'http://localhost:8000/auth/callback'

# Security
MAX_EMAIL_LENGTH = 50000

# CORS Origins
ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000"
]

# Allow insecure transport for local development ONLY
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
