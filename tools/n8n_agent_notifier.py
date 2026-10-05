#!/usr/bin/env python3
"""
n8n_agent_notifier.py
Servidor local de notificaciones HTTP robusto para recibir eventos de n8n.
"""

import sys
import os
import json
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 5679
LOG_FILE = "/tmp/n8n_agent_notifications.log"

class NotifierHandler(BaseHTTPRequestHandler):
    def handle_request(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else "{}"
        
        try:
            payload = json.loads(body)
        except Exception:
            payload = {"raw": body}
            
        status = payload.get("status", "UNKNOWN")
        wf_name = payload.get("workflow", "n8n Workflow")
        error_msg = payload.get("error", "")
        video_url = payload.get("video_url", "")
        project_dir = payload.get("project_dir", "")
        
        log_entry = {
            "status": status,
            "workflow": wf_name,
            "error": error_msg,
            "video_url": video_url,
            "project_dir": project_dir,
            "payload": payload
        }
        
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            
        print(f"[NOTIFIER] Event Received: Status={status} | Workflow={wf_name}", flush=True)
        if error_msg:
            print(f"[NOTIFIER] ERROR: {error_msg}", flush=True)
        if video_url:
            print(f"[NOTIFIER] VIDEO PUBLISHED: {video_url}", flush=True)

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        response = json.dumps({"status": "received"}).encode('utf-8')
        self.wfile.write(response)

    def do_POST(self):
        self.handle_request()

    def do_GET(self):
        self.handle_request()

    def log_message(self, format, *args):
        return

def run():
    server_address = ('0.0.0.0', PORT)
    httpd = HTTPServer(server_address, NotifierHandler)
    print(f"[NOTIFIER] Listening on 0.0.0.0:{PORT}...", flush=True)
    httpd.serve_forever()

if __name__ == "__main__":
    run()
