#!/usr/bin/env python3
"""
n8n Webhook Tester & Execution Monitor
Triggers an n8n webhook and automatically polls the execution API until completion,
reporting success/failure and error details cleanly.
Enforces Strict Single Execution Rule.
"""

import sys
import json
import time
import urllib.request
import urllib.error
import subprocess

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

def stop_running_executions(wf_id):
    if not wf_id:
        return
    cmd = ["python3", "/home/javierferb/n8n/tools/n8n_helper.py", "stop_all", wf_id]
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def _api_get(endpoint):
    url = f"{N8N_URL}{endpoint}"
    req = urllib.request.Request(url, headers={"X-N8N-API-KEY": API_KEY})
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

def trigger_webhook(webhook_url, payload=None):
    headers = {"Content-Type": "application/json"}
    data = json.dumps(payload or {}).encode("utf-8")
    req = urllib.request.Request(webhook_url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        if e.code == 404 and "GET request" in body:
            req_get = urllib.request.Request(webhook_url, headers=headers, method="GET")
            try:
                with urllib.request.urlopen(req_get) as resp_get:
                    return resp_get.status, resp_get.read().decode("utf-8")
            except urllib.error.HTTPError as e_get:
                return e_get.code, e_get.read().decode("utf-8")
        return e.code, body
    except Exception as e:
        return 500, str(e)

def get_latest_execution(wf_id):
    res_run = _api_get(f"/executions?workflowId={wf_id}&status=running&limit=1")
    if res_run and "data" in res_run and len(res_run["data"]) > 0:
        return res_run["data"][0]
    res = _api_get(f"/executions?workflowId={wf_id}&limit=1")
    if res and "data" in res and len(res["data"]) > 0:
        return res["data"][0]
    return None

def get_execution_by_id(exec_id):
    res = _api_get(f"/executions/{exec_id}?includeData=true")
    if res:
        return res
    return None

def watch_execution(wf_id=None, timeout_sec=3600, min_exec_id=0):
    start_time = time.time()
    print("Watching execution via n8n REST API...", flush=True)
    
    exec_id = None
    for _ in range(60):
        time.sleep(2)
        ex = get_latest_execution(wf_id)
        if ex:
            eid = ex.get("id")
            if int(eid) > int(min_exec_id):
                exec_id = eid
                break
            
    if not exec_id:
        print("No new execution recorded yet.")
        return False
        
    print(f"Tracking Execution ID: {exec_id}", flush=True)
    
    while time.time() - start_time < timeout_sec:
        ex = get_execution_by_id(exec_id)
        if ex:
            finished = ex.get("finished", False)
            status = str(ex.get("status", "")).lower()
            if finished or status in ["success", "error", "canceled", "crashed"]:
                print(f"\n--- EXECUTION COMPLETE ---")
                print(f"ID: {exec_id}")
                print(f"Status: {status.upper()}")
                print(f"Duration: {round(time.time() - start_time, 2)}s")
                if status in ["error", "crashed"]:
                    rd = ex.get("data", {}).get("resultData", {})
                    err = rd.get("error", {})
                    if err:
                        print(f"Error Message: {err.get('message')}")
                        print(f"Error Node: {err.get('node')}")
                    print("Execution failed. Check details in n8n UI or API.")
                    return False
                return True
        print(".", end="", flush=True)
        time.sleep(3)
    
    print("\nTimeout waiting for execution.")
    return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: webhook_tester.py <webhook_url> [workflow_id]")
        sys.exit(1)
        
    url = sys.argv[1]
    wf_id = sys.argv[2] if len(sys.argv) > 2 else "WfAmazonRank001"
    
    latest_ex = get_latest_execution(wf_id)
    max_id = latest_ex.get("id", 0) if latest_ex else 0

    # STRICT SINGLE EXECUTION ENFORCEMENT
    stop_running_executions(wf_id)
    
    print(f"Triggering Webhook: {url}")
    code, resp = trigger_webhook(url)
    print(f"Webhook Response Code: {code}")
    print(f"Webhook Response Body: {resp.strip()}")
    
    success = watch_execution(wf_id=wf_id, min_exec_id=max_id)
    sys.exit(0 if success else 1)
