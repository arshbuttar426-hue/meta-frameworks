#!/usr/bin/env python3
import http.server
import socketserver
import json
import os
from datetime import datetime

PORT = 8765

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        body = self.rfile.read(content_length)
        data = json.loads(body)
        
        # Log the alert
        alert_file = os.path.expanduser('~/NeuroCity/NeuroCity_Vault/latest_alert.txt')
        with open(alert_file, 'w') as f:
            f.write(data['message'] + '\n' + data['time'])
        
        # macOS notification
        os.system("""osascript -e 'display notification "%s" with title "NeuroCity Council"'""" % data['message'])
        
        self.send_response(200)
        self.end_headers()
    
    def log_message(self, format, *args):
        pass  # Silence logs

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print("Notifier listening on port " + str(PORT))
    httpd.serve_forever()
