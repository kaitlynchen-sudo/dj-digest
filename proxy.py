#!/usr/bin/env python3
"""
DJ Digest — OpenAI proxy
Runs on localhost:8765, forwards requests to OpenAI API.

Usage:
  python3 proxy.py
  Then enter your OpenAI API key in the banner at the top of index.html.
"""

import json, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 8765

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print(f"[proxy] {fmt % args}")

    def do_OPTIONS(self):
        self._send_cors(200)
        self.end_headers()

    def do_POST(self):
        length  = int(self.headers.get("Content-Length", 0))
        payload = json.loads(self.rfile.read(length))

        api_key = payload.pop("__api_key", "")

        # Convert Anthropic message format to OpenAI format
        messages = []
        if "system" in payload:
            messages.append({"role": "system", "content": payload["system"]})
        messages.extend(payload.get("messages", []))

        body = {
            "model": "gpt-4o",
            "max_tokens": payload.get("max_tokens", 1024),
            "messages": messages,
        }

        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(body).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )

        print(f"[proxy] --> OpenAI gpt-4o")
        try:
            with urllib.request.urlopen(req) as res:
                data = json.loads(res.read())
            # Convert OpenAI response to Anthropic format so index.html needs no changes
            result = {
                "content": [{"type": "text", "text": data["choices"][0]["message"]["content"]}]
            }
            print(f"[proxy] <-- 200 OK")
            self._send_cors(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        except urllib.error.HTTPError as e:
            body = e.read()
            print(f"[proxy] <-- {e.code} ERROR: {body.decode()}")
            self._send_cors(e.code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            print(f"[proxy] <-- EXCEPTION: {e}")
            self._send_cors(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": {"message": str(e)}}).encode())

    def _send_cors(self, code):
        self.send_response(code)
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

if __name__ == "__main__":
    print(f"[proxy] DJ Digest OpenAI proxy starting on http://localhost:{PORT}")
    print(f"[proxy] Enter your OpenAI API key in the page banner.")
    HTTPServer(("localhost", PORT), Handler).serve_forever()
