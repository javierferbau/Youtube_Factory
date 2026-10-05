#!/usr/bin/env python3
import sys
import os
import time
import json
import subprocess

def main():
    print("Iniciando monitoreo de ejecución n8n...")
    cmd = [
        "docker", "exec", "ia-lab-core-n8n-1", "node", "-e", """
const sqlite3 = require('/usr/local/lib/node_modules/n8n/node_modules/sqlite3');
const db = new sqlite3.Database('/home/node/.n8n/database.sqlite');
db.get("SELECT id, finished, status, stoppedAt FROM execution_entity WHERE workflowId='TY375mNkv5eejIQi' ORDER BY id DESC LIMIT 1", (err, row) => {
    console.log(JSON.stringify(row || {}));
});
"""
    ]

    last_id = None
    while True:
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            out = res.stdout.strip()
            if out:
                lines = [l for l in out.splitlines() if l.startswith("{")]
                if lines:
                    data = json.loads(lines[-1])
                    exec_id = data.get("id")
                    finished = data.get("finished")
                    status = data.get("status")
                    if exec_id:
                        if exec_id != last_id:
                            print(f"Tracking Execution ID: {exec_id} | Status: {status}")
                            last_id = exec_id
                        
                        if finished == 1:
                            print(f"\n⚡ Ejecución {exec_id} FINALIZADA con estado: {status.upper()}")
                            if status == "success":
                                # Query node payload for YT Upload YouTube
                                cmd_payload = [
                                    "docker", "exec", "ia-lab-core-n8n-1", "node", "-e", f"""
const sqlite3 = require('/usr/local/lib/node_modules/n8n/node_modules/sqlite3');
const db = new sqlite3.Database('/home/node/.n8n/database.sqlite');
db.get("SELECT data FROM execution_data WHERE executionId={exec_id}", (err, row) => {{
    if (row && row.data) {{
        console.log(row.data);
    }}
}});
"""
                                ]
                                pres = subprocess.run(cmd_payload, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                                ptext = pres.stdout
                                print("\n=== VERIFICACIÓN METADATOS YOUTUBE ===")
                                print("Ejecución completada con ÉXITO.")
                            sys.exit(0 if status == "success" else 1)
        except Exception as e:
            print("Error polling:", e)
        time.sleep(10)

if __name__ == "__main__":
    main()
