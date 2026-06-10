#!/usr/bin/env python3
"""Simple web application server."""

import http.server
import json

class AppHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        response = {"status": "ok", "app": "webapp"}
        self.wfile.write(json.dumps(response).encode())

if __name__ == "__main__":
    server = http.server.HTTPServer(("0.0.0.0", 8080), AppHandler)
    server.serve_forever()
