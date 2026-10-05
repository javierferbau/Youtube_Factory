#!/usr/bin/env python3
"""
upload_to_youtube.py
Uploads a video to YouTube using Python google-api-python-client & stored credentials from n8n SQLite DB.
"""

import sys
import os
import json
import sqlite3
import urllib.request
import urllib.parse
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

if len(sys.argv) < 2:
    print("Usage: upload_to_youtube.py <project_dir>", file=sys.stderr)
    sys.exit(1)

project_dir = sys.argv[1]

# 1. Load optimized metadata
meta_file = os.path.join(project_dir, "youtube_optimized.json")
if not os.path.exists(meta_file):
    meta_file = os.path.join(project_dir, "youtube_metadata.json")

if not os.path.exists(meta_file):
    print(f"Error: {meta_file} does not exist", file=sys.stderr)
    sys.exit(1)

with open(meta_file, "r", encoding="utf-8") as f:
    meta = json.load(f)

title = meta.get("youtube_title") or meta.get("title", "Ranking Productos Amazon 2026")
description = meta.get("description", "")
tags = meta.get("tags", [])
privacy_status = meta.get("privacy_status", "private")
category_id = str(meta.get("category_id", "28"))

video_file = os.path.join(project_dir, "RENDER_FINAL_AMAZON.mp4")
if not os.path.exists(video_file):
    print(f"Error: Video {video_file} not found", file=sys.stderr)
    sys.exit(1)

print(json.dumps({"status": "ready", "title": title, "tags_count": len(tags), "video_file": video_file}))
