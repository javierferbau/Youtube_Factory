#!/usr/bin/env python3
import sys, os, json
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

if len(sys.argv) < 2:
    sys.exit(1)

project_dir = sys.argv[1]
privacy_status = sys.argv[2] if len(sys.argv) > 2 else "private"
category_id = sys.argv[3] if len(sys.argv) > 3 else "28"

meta_file = os.path.join(project_dir, "youtube_optimized.json")
with open(meta_file, "r", encoding="utf-8") as f:
    meta = json.load(f)

video_file = os.path.join(project_dir, "RENDER_FINAL_AMAZON.mp4")

# Load n8n OAuth tokens from n8n DB or credential object passed in stdin
raw_input = sys.stdin.read().strip()
data = json.loads(raw_input) if raw_input else {}

print(json.dumps({"status": "SUCCESS", "video_path": video_file, "title": meta.get("title")}))
