#!/usr/bin/env python3
"""
Web GUI launcher for NLMandSlideVideoGenerator
"""

import subprocess
import sys
import time
import webbrowser
from pathlib import Path

def main():
    """Launch Streamlit web application"""
    project_root = Path(__file__).parent

    # Change to project root directory
    import os
    os.chdir(project_root)

    # Launch streamlit in background
    cmd = [sys.executable, "-m", "streamlit", "run", "src/web/web_app.py",
           "--server.port", "8502",
           "--server.address", "0.0.0.0",
           "--server.headless", "false",
           "--browser.gatherUsageStats", "false"]
    print("Starting Streamlit GUI...")
    print(f"Command: {' '.join(cmd)}")
    try:
        process = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        print("Subprocess started, PID:", process.pid)
        # Send newline to skip email prompt
        process.stdin.write(b'\n')
        process.stdin.flush()
    except Exception as e:
        print(f"Failed to start subprocess: {e}")
        return

    # Wait a moment for server to start
    time.sleep(3)

    # Open browser
    url = "http://localhost:8502"
    print(f"Opening browser at {url}")
    try:
        # Try webbrowser first
        result = webbrowser.open(url)
        print(f"webbrowser.open result: {result}")
        if not result:
            # Fallback to start command on Windows
            print("Trying start command...")
            subprocess.run(["start", url], shell=True)
    except Exception as e:
        print(f"Browser open failed: {e}")
        print("Please manually open the URL in your browser")

    # Wait for process to finish
    try:
        process.wait()
    except KeyboardInterrupt:
        print("Shutting down GUI...")
        process.terminate()

if __name__ == "__main__":
    main()
