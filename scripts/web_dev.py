"""Local development server for the cloud chat UI and its Vercel handler.

Set JARVIS_ACCESS_KEY and AI_GATEWAY_API_KEY in the environment first. Bind to
0.0.0.0 so an Arena preview works; do not use this development server for
production or expose it without the access key.
"""

from __future__ import annotations

import argparse
import contextlib
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.chat import handler as ChatHandler  # noqa: E402


class DevHandler(ChatHandler, SimpleHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if urlsplit(self.path).path == "/api/chat":
            ChatHandler.do_GET(self)
        else:
            SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self) -> None:  # noqa: N802
        if urlsplit(self.path).path == "/api/chat":
            ChatHandler.do_POST(self)
        else:
            self.send_error(404)

    def do_HEAD(self) -> None:  # noqa: N802
        if urlsplit(self.path).path == "/api/chat":
            self.send_error(405)
        else:
            SimpleHTTPRequestHandler.do_HEAD(self)


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the JARVIS cloud web app locally")
    parser.add_argument("--port", type=int, default=4173)
    args = parser.parse_args()
    handler = partial(DevHandler, directory=str(ROOT / "web"))
    with ThreadingHTTPServer(("0.0.0.0", args.port), handler) as server:
        print(f"JARVIS web preview listening on port {args.port}", flush=True)
        with contextlib.suppress(KeyboardInterrupt):
            server.serve_forever()


if __name__ == "__main__":
    main()
