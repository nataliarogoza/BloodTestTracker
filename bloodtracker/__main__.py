""" Run the app with: python -m bloodtracker [--no-browser] """
import argparse
import threading
import webbrowser

import uvicorn

from bloodtracker.config import HOST, PORT


def main():
    parser = argparse.ArgumentParser(description="Run BloodTestTracker locally")
    parser.add_argument("--no-browser", action="store_true", help="don't open a browser tab")
    args = parser.parse_args()

    url = f"http://{HOST}:{PORT}"
    print(f"BloodTestTracker running at {url} (Ctrl+C to stop)")
    if not args.no_browser:
        threading.Timer(1.0, webbrowser.open, args=[url]).start() # Give the server a moment to start
    uvicorn.run("bloodtracker.app:create_app", factory=True, host=HOST, port=PORT)


if __name__ == "__main__":
    main()
