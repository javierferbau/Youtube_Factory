#!/usr/bin/env python3
import sys
import json
import subprocess
import argparse

def get_process_list():
    cmd = ["ps", "aux"]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    lines = res.stdout.strip().split("\n")
    processes = []
    for line in lines[1:]:
        parts = line.split(None, 10)
        if len(parts) >= 11:
            user, pid, cpu, mem, vsz, rss, tty, stat, start, time, command = parts
            if any(k in command for k in ["ffmpeg", "yt-dlp", "n8n"]):
                processes.append({
                    "pid": pid,
                    "user": user,
                    "cpu_pct": float(cpu),
                    "mem_pct": float(mem),
                    "time": time,
                    "command": command[:120]
                })
    return processes

def get_docker_stats():
    cmd = ["docker", "stats", "--no-stream", "--format", "{{json .}}"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        stats = []
        for line in res.stdout.strip().split("\n"):
            if line:
                stats.append(json.loads(line))
        return stats
    except Exception as e:
        return [{"error": str(e)}]

def kill_runaway_processes(max_elapsed_sec=900, dry_run=False):
    cmd = ["ps", "-eo", "pid,etimes,comm,args"]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    lines = res.stdout.strip().split("\n")
    terminated = []
    for line in lines[1:]:
        parts = line.strip().split(None, 3)
        if len(parts) >= 4:
            pid, etimes, comm, args = parts
            try:
                etime = int(etimes)
            except ValueError:
                continue
            exe = args.split()[0].lower() if args else ""
            is_ffmpeg = comm.lower() == "ffmpeg" or exe.endswith("/ffmpeg") or exe == "ffmpeg"
            if is_ffmpeg:
                if etime > max_elapsed_sec:
                    if not dry_run:
                        subprocess.run(["kill", "-9", pid], check=False)
                    terminated.append({
                        "pid": pid,
                        "elapsed_seconds": etime,
                        "action": "killed" if not dry_run else "would_kill",
                        "command": args[:120]
                    })
    return terminated

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Watchdog de Procesos y Contenedores")
    parser.add_argument("--kill-runaways", action="store_true", help="Mata procesos ffmpeg colgados (>15m)")
    parser.add_argument("--max-seconds", type=int, default=900, help="Segundos maximos")
    parser.add_argument("--dry-run", action="store_true", help="Simulacion")
    args = parser.parse_args()

    terminated = []
    if args.kill_runaways:
        terminated = kill_runaway_processes(max_elapsed_sec=args.max_seconds, dry_run=args.dry_run)

    report = {
        "heavy_processes": get_process_list(),
        "docker_containers": get_docker_stats(),
        "terminated_runaways": terminated
    }
    print(json.dumps(report, indent=2))
