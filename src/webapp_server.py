"""Simple web server for Telegram Web App."""

import os
import logging
from http.server import HTTPServer, SimpleHTTPRequestHandler
from threading import Thread
from urllib.parse import unquote

logger = logging.getLogger(__name__)


class WebAppHandler(SimpleHTTPRequestHandler):
    """Custom handler for serving web app files."""

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

    def start(self):
        """Start the web server in a background thread."""
        try:
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
