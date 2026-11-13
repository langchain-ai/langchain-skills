"""Tools service for the support assistant: documentation search and tickets."""

from __future__ import annotations

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

HOST = "127.0.0.1"
PORT = int(os.environ.get("TOOLS_SERVICE_PORT", "8765"))

ARTICLES = [
    {"id": "kb-101", "title": "Rotate an API key", "keywords": ["api key", "rotate", "old key"],
     "body": "Create a new key in Settings, update your services, then revoke the old key. "
             "A revoked key stops working immediately."},
    {"id": "kb-204", "title": "Traces are not appearing", "keywords": ["traces", "dashboard", "no traces"],
     "body": "Check the API key, the endpoint for your region, and that tracing is enabled."},
    {"id": "kb-310", "title": "Supported regions", "keywords": ["region", "regions", "eu"],
     "body": "Accounts are hosted in the US or EU region. Moving an existing workspace between "
             "regions requires a migration request through support."},
]

_tickets: list[dict] = []


def handle_search_request(payload: dict) -> dict:
    query = payload.get("query", "").lower()
    matches = [a for a in ARTICLES if any(k in query for k in a["keywords"])]
    return {"articles": [{"id": a["id"], "title": a["title"], "body": a["body"]} for a in matches]}


def handle_ticket_request(payload: dict) -> dict:
    ticket = {"ticket_id": f"TCK-{1001 + len(_tickets)}", "summary": payload.get("summary", ""), "status": "open"}
    _tickets.append(ticket)
    return ticket


ROUTES = {"/search_docs": handle_search_request, "/create_ticket": handle_ticket_request}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/health":
            self._reply(200, {"status": "ok"})
        else:
            self._reply(404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path == "/shutdown":
            self._reply(200, {"status": "stopping"})
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return
        route = ROUTES.get(self.path)
        if route is None:
            self._reply(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length) or b"{}")
        self._reply(200, route(payload))

    def _reply(self, status: int, body: dict) -> None:
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    server = HTTPServer((HOST, PORT), Handler)
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
