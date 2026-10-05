#!/usr/bin/env python3
import sys, os, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    cmd = [
        sys.executable,
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "random_vs_topic.py"),
        "--channel_name", "El Taller del Pueblo",
        "--channel_niche", "herramientas eléctricas, bricolaje, taladros y amoladoras"
    ] + sys.argv[1:]
    subprocess.run(cmd)
