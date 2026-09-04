"""
Web Dashboard & REST API HTTP Server.

Serves the Enterprise Banking AI Automation Dashboard UI and handles REST API requests
for live Multi-Agent test triggering, HITL ratifications, and audit ledger queries.
"""

from __future__ import annotations

import http.server
import json
import logging
import os
import socketserver
import sys
from typing import Any, Dict

from src.hitl.api import HITLAPIController

logger = logging.getLogger("BankAI.DashboardServer")

PORT = 8080
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

api_controller = HITLAPIController()


class BankAIDashboardHandler(http.server.SimpleHTTPRequestHandler):
    """
    HTTP Request Handler combining static Dashboard UI serving with API endpoints.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def do_GET(self) -> None:
        """Route GET requests to API controllers or static UI files."""
        if self.path == "/api/summary":
            self._send_json_response(api_controller.get_dashboard_summary())
        elif self.path == "/api/pending":
            self._send_json_response(api_controller.list_pending_reviews())
        else:
            super().do_GET()

    def do_POST(self) -> None:
        """Route POST API requests for run triggering and ratification."""
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b"{}"

        try:
            body: Dict[str, Any] = json.loads(post_data.decode("utf-8")) if post_data else {}
        except json.JSONDecodeError:
            body = {}

        if self.path == "/api/trigger":
            req = body.get("requirement", "Validate cross-border payment")
            journey = body.get("journey_type", "CROSS_BORDER_PAYMENT")
            persona = body.get("persona", "corporate_treasurer")
            res = api_controller.trigger_test_run(req, journey, persona)
            self._send_json_response(res)

        elif self.path == "/api/ratify":
            item_id = body.get("item_id", "")
            approved = bool(body.get("approved", True))
            reviewer = body.get("reviewer_id", "qa_lead_01")
            comments = body.get("comments", "Ratified via dashboard")
            res = api_controller.submit_ratification(item_id, approved, reviewer, comments)
            self._send_json_response(res)

        else:
            self.send_error(404, "API Endpoint Not Found")

    def _send_json_response(self, data: Any, status_code: int = 200) -> None:
        """Send JSON HTTP response."""
        response_bytes = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(response_bytes)


def start_server(port: int = PORT):
    """Start local web dashboard server."""
    with socketserver.TCPServer(("", port), BankAIDashboardHandler) as httpd:
        print(f"===========================================================")
        print(f"  BankAI Enterprise Dashboard running at: http://localhost:{port}")
        print(f"===========================================================")
        httpd.serve_forever()


if __name__ == "__main__":
    start_server()
