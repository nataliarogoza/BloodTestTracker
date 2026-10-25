""" Run the app with: python -m bloodtracker [--no-browser] """
import argparse
import socket
import sys
import threading
import webbrowser

import uvicorn

from bloodtracker.config import HOST, PORT


def port_is_free(host: str, port: int) -> bool:
    """ True if nothing is listening on the port yet """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # The same setting Uvicorn uses
        try:
            probe.bind((host, port))
        except OSError:
            return False
    return True


def port_in_use_message(host: str, port: int) -> str:
    return (f"Port {port} is already in use - most likely BloodTestTracker is already running\n"
            f"(or paused with Ctrl+Z) in another terminal. You can:\n"
            f"  - open the running one: http://{host}:{port}\n"
            f"  - stop it: in its terminal type fg, press Enter, then press Ctrl+C\n"
            f"  - or start this one on another port: BLOODTRACKER_PORT={port + 1} python -m bloodtracker")


def main(argv: list[str] | None = None, host: str = HOST, port: int = PORT):
    parser = argparse.ArgumentParser(description="Run BloodTestTracker locally")
    parser.add_argument("--no-browser", action="store_true", help="don't open a browser tab")
    args = parser.parse_args(argv)

    if not port_is_free(host, port): # Clearer than Uvicorn's "[Errno 98] address already in use"
        sys.exit(port_in_use_message(host, port))

    url = f"http://{host}:{port}"
    print(f"BloodTestTracker running at {url} (Ctrl+C to stop)")
    if not args.no_browser:
        threading.Timer(1.0, webbrowser.open, args=[url]).start() # Give the server a moment to start
    uvicorn.run("bloodtracker.app:create_app", factory=True, host=host, port=port)


if __name__ == "__main__":
    main()
