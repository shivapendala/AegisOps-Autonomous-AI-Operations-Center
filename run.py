"""
AegisOps - Single Command Full-Stack Launcher.
Run with:
    python run.py

Starts both the FastAPI Backend and the React Frontend,
and automatically opens the dashboard in your default browser.
"""

import os
import platform
import subprocess
import sys
import time
import urllib.request
import webbrowser

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(ROOT_DIR, "frontend")
BACKEND_HOST = "127.0.0.1"
BACKEND_PORT = 8000
FRONTEND_PORT = 5173

BACKEND_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}"
FRONTEND_URL = f"http://localhost:{FRONTEND_PORT}"


def wait_for_service(url: str, timeout: float = 15.0) -> bool:
    """Polls a URL until it returns HTTP 200 or timeout expires."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=1.5) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def main():
    print("=" * 65)
    print("     🛡️  AegisOps - Autonomous AI Operations Center  🛡️     ")
    print("=" * 65)
    print("\n[1/3] Starting FastAPI Backend + Real-Time Monitoring...")

    # Determine command executables based on OS
    is_windows = platform.system() == "Windows"
    npm_cmd = "npm.cmd" if is_windows else "npm"

    # Start FastAPI Backend
    backend_proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.main:app",
            "--host",
            BACKEND_HOST,
            "--port",
            str(BACKEND_PORT),
        ],
        cwd=ROOT_DIR,
    )

    # Wait for backend readiness
    print("      Waiting for backend to initialize...")
    if wait_for_service(f"{BACKEND_URL}/api/health", timeout=12.0):
        print("      ✅ Backend ready at", BACKEND_URL)
    else:
        print("      ⚠️  Backend started, continuing...")

    # Start React Frontend (Vite)
    print("\n[2/3] Starting React + TypeScript Frontend...")
    frontend_proc = subprocess.Popen(
        [npm_cmd, "run", "dev"],
        cwd=FRONTEND_DIR,
    )

    # Wait for frontend readiness
    print("      Waiting for Vite development server...")
    if wait_for_service(FRONTEND_URL, timeout=12.0):
        print("      ✅ Frontend ready at", FRONTEND_URL)
    else:
        print("      ✅ Frontend launching...")

    # Open Dashboard in default web browser
    print("\n[3/3] Opening AegisOps Dashboard in browser...")
    time.sleep(1.0)
    webbrowser.open(FRONTEND_URL)

    print("\n" + "=" * 65)
    print("🚀  AegisOps is live and running!")
    print("=" * 65)
    print(f"  • Frontend Dashboard:  {FRONTEND_URL}")
    print(f"  • API Documentation:   {BACKEND_URL}/docs")
    print(f"  • Health Endpoint:     {BACKEND_URL}/api/health")
    print(f"  • WebSocket Stream:    ws://{BACKEND_HOST}:{BACKEND_PORT}/ws/monitor")
    print("=" * 65)
    print("\nPress Ctrl + C in this terminal anytime to stop all services.\n")

    try:
        # Keep alive while child processes are running
        while True:
            time.sleep(1)
            # If any process terminated unexpectedly, exit
            if backend_proc.poll() is not None:
                print("\n[Notice] Backend process exited.")
                break
            if frontend_proc.poll() is not None:
                print("\n[Notice] Frontend process exited.")
                break
    except KeyboardInterrupt:
        print("\n\nShutting down AegisOps services gracefully...")
    finally:
        # Gracefully terminate child processes
        if backend_proc.poll() is None:
            backend_proc.terminate()
            try:
                backend_proc.wait(timeout=3)
            except Exception:
                backend_proc.kill()

        if frontend_proc.poll() is None:
            frontend_proc.terminate()
            try:
                frontend_proc.wait(timeout=3)
            except Exception:
                frontend_proc.kill()

        print("All services stopped. Goodbye!")


if __name__ == "__main__":
    main()
