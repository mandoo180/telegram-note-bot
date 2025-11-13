"""Simple web server for Telegram Web App."""

import os
import logging
import secrets
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from threading import Thread, Lock
from urllib.parse import urlparse, parse_qs

logger = logging.getLogger(__name__)


class TokenManager:
    """Manage one-time access tokens for Web App security."""

    def __init__(self, expiry_seconds=300):
        """Initialize token manager.

        Args:
            expiry_seconds: How long tokens are valid (default: 5 minutes)
        """
        self.tokens = {}  # {token: (timestamp, used)}
        self.lock = Lock()
        self.expiry_seconds = expiry_seconds

    def generate_token(self) -> str:
        """Generate a new secure token."""
        token = secrets.token_urlsafe(32)
        with self.lock:
            self.tokens[token] = (time.time(), False)
            self._cleanup_expired()
        return token

    def validate_and_consume(self, token: str) -> bool:
        """Validate a token and mark it as used (one-time use).

        Args:
            token: The token to validate

        Returns:
            True if valid and not yet used, False otherwise
        """
        if not token:
            return False

        with self.lock:
            self._cleanup_expired()

            if token not in self.tokens:
                return False

            timestamp, used = self.tokens[token]

            # Check if token is expired
            if time.time() - timestamp > self.expiry_seconds:
                del self.tokens[token]
                return False

            # Check if already used
            if used:
                return False

            # Mark as used
            self.tokens[token] = (timestamp, True)
            return True

    def _cleanup_expired(self):
        """Remove expired tokens."""
        current_time = time.time()
        expired = [
            token for token, (timestamp, _) in self.tokens.items()
            if current_time - timestamp > self.expiry_seconds
        ]
        for token in expired:
            del self.tokens[token]


class WebAppHandler(SimpleHTTPRequestHandler):
    """Custom handler for serving web app files."""

    token_manager = None  # Will be set by WebAppServer

    def __init__(self, *args, **kwargs):
        # Set the directory to serve files from
        super().__init__(*args, directory='webapp', **kwargs)

    def log_message(self, format, *args):
        """Override to use our logger instead of stderr."""
        logger.info(f"WebApp: {format % args}")

    def end_headers(self):
        """Add CORS headers for Telegram Web App."""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_GET(self):
        """Handle GET requests with token validation."""
        # Parse URL and query parameters
        parsed = urlparse(self.path)
        query_params = parse_qs(parsed.query)

        # Check if this is a protected Web App page
        if parsed.path.endswith(('note_editor.html', 'schedule_editor.html')):
            # Extract token from query parameters
            token_list = query_params.get('_token', [])
            token = token_list[0] if token_list else None

            # Validate token
            if not self.token_manager or not self.token_manager.validate_and_consume(token):
                logger.warning(f"Unauthorized access attempt to {parsed.path} (invalid token)")
                self.send_response(403)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                html_response = """
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>Access Denied</title>
                        <meta charset="UTF-8">
                        <meta name="viewport" content="width=device-width, initial-scale=1.0">
                    </head>
                    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; text-align: center; padding: 50px; max-width: 500px; margin: 0 auto;">
                        <h1 style="color: #e74c3c;">🔒 Access Denied</h1>
                        <p style="font-size: 18px; margin: 20px 0;">This page can only be accessed through the Telegram Bot.</p>
                        <p style="color: #7f8c8d;">Please use the appropriate command in your Telegram bot to access this editor.</p>
                        <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
                        <p style="font-size: 14px; color: #95a5a6;">If you believe this is an error, please try again from the bot.</p>
                    </body>
                    </html>
                """
                self.wfile.write(html_response.encode('utf-8'))
                return

        # If validation passed or not a protected page, serve normally
        super().do_GET()


class WebAppServer:
    """Web server for hosting Telegram Web App files."""

    def __init__(self, host='0.0.0.0', port=8000):
        """Initialize web server.

        Args:
            host: Host to bind to
            port: Port to bind to
        """
        self.host = host
        self.port = port
        self.server = None
        self.thread = None
        self.token_manager = TokenManager(expiry_seconds=300)  # 5 minute expiry

    def generate_token(self) -> str:
        """Generate a new access token for Web App.

        Returns:
            A secure one-time token
        """
        return self.token_manager.generate_token()

    def start(self):
        """Start the web server in a background thread."""
        try:
            # Set token manager on handler class
            WebAppHandler.token_manager = self.token_manager

            self.server = HTTPServer((self.host, self.port), WebAppHandler)
            self.thread = Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            logger.info(f"WebApp server started on http://{self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to start WebApp server: {e}")
            raise

    def stop(self):
        """Stop the web server."""
        if self.server:
            self.server.shutdown()
            logger.info("WebApp server stopped")

    def get_url(self, path='', base_url=None):
        """Get the full URL for a path.

        Args:
            path: Path relative to webapp directory
            base_url: Base URL to use (overrides default)

        Returns:
            Full URL to the resource
        """
        if base_url:
            return f"{base_url.rstrip('/')}/{path}"
        return f"http://localhost:{self.port}/{path}"
