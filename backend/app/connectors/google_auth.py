import os
import logging
from typing import List, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from wsgiref.simple_server import make_server
import wsgiref.util
from app.config import settings

logger = logging.getLogger(__name__)

# Shared scopes for Gmail and Google Calendar read-only access
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly"
]

# In-memory cache to prevent multiple OAuth flow runs in the same execution process
_cached_credentials = None
_oauth_attempted = False

class _RedirectWSGIApp:
    """
    Minimal WSGI application to capture the redirect callback URI from Google OAuth.
    """
    def __init__(self):
        self.last_request_uri = None

    def __call__(self, environ, start_response):
        start_response("200 OK", [
            ("Content-type", "text/html; charset=utf-8"),
            ("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        ])
        self.last_request_uri = wsgiref.util.request_uri(environ)
        
        # HTML response to show the user in their browser
        html = """
        <html>
        <head><title>Authentication Complete</title></head>
        <body style="font-family: sans-serif; text-align: center; padding-top: 50px; background-color: #121212; color: #ffffff;">
            <h2 style="color: #4CAF50;">Authentication Successful!</h2>
            <p>The token has been generated. You can close this tab and return to the terminal.</p>
        </body>
        </html>
        """
        return [html.encode("utf-8")]

def get_google_credentials() -> Optional[Credentials]:
    """
    Get or refresh Google OAuth2 credentials.
    Reads backend/credentials.json for client config and writes backend/token.json for session token caching.
    Uses a custom WSGI server inside the container to handle the redirect callback safely.
    """
    global _cached_credentials, _oauth_attempted

    # Return cached credentials if already fetched in this run
    if _cached_credentials and _cached_credentials.valid:
        return _cached_credentials

    # If we already tried and failed/skipped, don't try again in the same run to avoid port conflicts
    if _oauth_attempted and not _cached_credentials:
        logger.debug("Google OAuth was already attempted and failed/skipped. Returning None.")
        return None

    creds = None
    token_path = os.path.join(settings.BASE_DIR, "token.json")
    credentials_path = os.path.join(settings.BASE_DIR, "credentials.json")

    # Try loading from token.json
    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            logger.info("Loaded Google credentials from cached token.json")
        except Exception as e:
            logger.warning(f"Failed to load cached credentials: {str(e)}. Re-authenticating...")

    # Refresh token if expired
    if creds and not creds.valid:
        if creds.expired and creds.refresh_token:
            try:
                logger.info("Google credentials expired. Attempting to refresh...")
                creds.refresh(Request())
                with open(token_path, "w") as token_file:
                    token_file.write(creds.to_json())
                logger.info("Successfully refreshed Google credentials.")
            except Exception as e:
                logger.error(f"Failed to refresh token: {str(e)}. Forcing new login...")
                creds = None

    # Perform full OAuth flow if credentials are not valid or missing
    if not creds:
        _oauth_attempted = True
        if not os.path.exists(credentials_path):
            logger.error(
                f"Google client secrets credentials file NOT found at {credentials_path}. "
                "Please download OAuth 2.0 Desktop Application credentials from the Google Cloud Console "
                "and place them at this location."
            )
            return None

        try:
            # Allow HTTP for local/Docker OAuth (oauthlib enforces HTTPS by default)
            os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
            
            logger.info("Starting Custom Google OAuth 2.0 flow for Docker...")
            # Google requires localhost for loopback redirects
            redirect_uri = "http://localhost:8080/"
            
            flow = Flow.from_client_secrets_file(
                credentials_path, 
                scopes=SCOPES, 
                redirect_uri=redirect_uri
            )
            
            auth_url, _ = flow.authorization_url(
                access_type="offline", 
                prompt="consent",
                include_granted_scopes="true"
            )
            
            print(f"\n==================================================")
            print(f"Go to the following link in your browser to authorize:")
            print(f"{auth_url}")
            print(f"==================================================\n", flush=True)
            
            # Start WSGI server inside Docker binding to 0.0.0.0:8080 to receive callback
            wsgi_app = _RedirectWSGIApp()
            server = make_server("0.0.0.0", 8080, wsgi_app)
            
            # Block and handle exactly one request
            server.handle_request()
            server.server_close()
            
            # Extract and parse the response URI
            callback_url = wsgi_app.last_request_uri
            if not callback_url:
                raise Exception("Did not receive callback URL from browser redirect.")
                
            # Replace 0.0.0.0:8080 (or container IP) with localhost:8080 to satisfy oauthlib validation checks
            if "0.0.0.0:8080" in callback_url:
                callback_url = callback_url.replace("0.0.0.0:8080", "localhost:8080")
            elif "127.0.0.1:8080" in callback_url:
                callback_url = callback_url.replace("127.0.0.1:8080", "localhost:8080")
            elif "localhost" not in callback_url:
                # Fallback replacement for container host headers
                import re
                callback_url = re.sub(r'http://[^/]+:8080', 'http://localhost:8080', callback_url)

            # Exchange authorization code for tokens
            flow.fetch_token(authorization_response=callback_url)
            creds = flow.credentials
            
            # Save the credentials to token.json
            with open(token_path, "w") as token_file:
                token_file.write(creds.to_json())
            logger.info(f"Successfully cached Google credentials to {token_path}")
            
        except Exception as e:
            logger.error(f"Google OAuth flow failed: {str(e)}")
            return None

    _cached_credentials = creds
    return creds
