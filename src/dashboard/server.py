"""
Web Dashboard Local HTTP Server.

Serves the Enterprise Banking AI Automation Dashboard UI locally.
"""

from __future__ import annotations

import http.server
import socketserver
import os
import sys
import logging

logger = logging.getLogger("BankAI.DashboardServer")

PORT = 8080
DIRECTORY = os.path.dirname(os.path.abspath(__file__))


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)


def start_server(port: int = PORT):
    """Start local web dashboard server."""
    with socketserver.TCPServer(("", port), Handler) as httpd:
        print(f"===========================================================")
        print(f"  BankAI Dashboard running at: http://localhost:{port}")
        print(f"===========================================================")
        httpd.serve_forever()


if __name__ == "__main__":
    start_server()
