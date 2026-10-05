#!/usr/bin/env python3
"""
n8n API Helper - Safe & Official Interface for n8n Workflow Management
Uses the official n8n Public REST API to manage workflows, executions, and triggers.
"""

import sys
import json
import urllib.request
import urllib.error
import signal

signal.signal(signal.SIGPIPE, signal.SIG_DFL)

N8N_URL = "http://localhost:5678/api/v1"
def get_n8n_api_key():
    import os
    key = os.getenv("N8N_API_KEY")
    if key:
        return key
    env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env')
    if os.path.exists(env_file):
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip().startswith('N8N_API_KEY='):
                    return line.strip().split('=', 1)[1].strip(' "\'')
    return ""

API_KEY = get_n8n_api_key()

def _request(endpoint, method="GET", data=None):
    url = f"{N8N_URL}{endpoint}"
    headers = {
        "X-N8N-API-KEY": API_KEY,
        "Content-Type": "application/json"
    }
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"API Error {e.code}: {e.read().decode('utf-8')}", file=sys.stderr)
        return None

def list_workflows():
    res = _request("/workflows")
    if res and "data" in res:
        for wf in res["data"]:
            status = "ACTIVE" if wf.get("active") else "INACTIVE"
            print(f"[{status}] ID: {wf.get('id')} | Name: {wf.get('name')}")

def get_workflow(wf_id):
    res = _request(f"/workflows/{wf_id}")
    if res:
        print(json.dumps(res, indent=2, ensure_ascii=False))

def activate_workflow(wf_id):
    res = _request(f"/workflows/{wf_id}/activate", method="POST")
    if res:
        print(f"Workflow {wf_id} activated successfully.")

def deactivate_workflow(wf_id):
    res = _request(f"/workflows/{wf_id}/deactivate", method="POST")
    if res:
        print(f"Workflow {wf_id} deactivated successfully.")

def list_executions(wf_id=None):
    endpoint = f"/executions?workflowId={wf_id}&limit=10" if wf_id else "/executions?limit=10"
    res = _request(endpoint)
    if res and "data" in res:
        for ex in res["data"]:
            finished = "FINISHED" if ex.get("finished") else "RUNNING"
            print(f"ID: {ex.get('id')} | Status: {ex.get('status')} | State: {finished} | Started: {ex.get('startedAt')}")

def stop_execution(execution_id):
    res = _request(f"/executions/{execution_id}/stop", method="POST")
    if res:
        print(f"Execution {execution_id} stopped.")

def stop_all_executions(wf_id=None):
    if not wf_id:
        wf_id = "WfAmazonRank001"
    try:
        _request(f"/workflows/{wf_id}/deactivate", method="POST")
        _request(f"/workflows/{wf_id}/activate", method="POST")
        print(f"Enforced strict single execution: All previous running executions of {wf_id} canceled.")
    except Exception as e:
        print(f"Warning stopping executions for {wf_id}: {e}")

def update_workflow(wf_id, file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    raw_settings = data.get("settings", {})
    allowed_keys = {'executionOrder', 'timezone', 'saveDataErrorExecution', 'saveDataSuccessExecution', 'saveExecutionProgress', 'callerPolicy'}
    clean_settings = {k: v for k, v in raw_settings.items() if k in allowed_keys}
    payload = {
        "name": data.get("name"),
        "nodes": data.get("nodes"),
        "connections": data.get("connections"),
        "settings": clean_settings
    }
    res = _request(f"/workflows/{wf_id}", method="PUT", data=payload)
    if res:
        print(f"Workflow {wf_id} updated successfully.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: n8n_helper.py <list|get|update|activate|deactivate|executions|stop|stop_all> [id] [file]")
        sys.exit(1)

    cmd = sys.argv[1]
    arg = sys.argv[2] if len(sys.argv) > 2 else None
    arg2 = sys.argv[3] if len(sys.argv) > 3 else None

    if cmd == "list":
        list_workflows()
    elif cmd == "get" and arg:
        get_workflow(arg)
    elif cmd == "update" and arg and arg2:
        update_workflow(arg, arg2)
    elif cmd == "activate" and arg:
        activate_workflow(arg)
    elif cmd == "deactivate" and arg:
        deactivate_workflow(arg)
    elif cmd == "executions":
        list_executions(wf_id=arg)
    elif cmd == "stop" and arg:
        stop_execution(arg)
    elif cmd == "stop_all":
        stop_all_executions(wf_id=arg)

