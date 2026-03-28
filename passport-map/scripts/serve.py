from __future__ import annotations

import contextlib
import os
import socket
import sys
import threading
import time
import webbrowser
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PORT_CANDIDATES = [8010, 8011, 8012, 8020, 8080]
URL_FILE = PROJECT_ROOT / ".tmp" / "server-url.txt"


def find_available_port() -> int:
    for port in PORT_CANDIDATES:
        with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError("没有找到可用端口")


def main() -> int:
    os.chdir(PROJECT_ROOT)
    URL_FILE.parent.mkdir(parents=True, exist_ok=True)
    if URL_FILE.exists():
        URL_FILE.unlink()

    try:
        port = find_available_port()
    except RuntimeError as error:
        print(str(error))
        input("按回车退出...")
        return 1

    server = ThreadingHTTPServer(("127.0.0.1", port), SimpleHTTPRequestHandler)
    url = f"http://127.0.0.1:{port}"
    URL_FILE.write_text(url, encoding="utf-8")

    print(f"本地页面已启动：{url}", flush=True)
    print("关闭这个窗口就会停止服务。", flush=True)

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    time.sleep(1)
    webbrowser.open(url)

    try:
        thread.join()
    except KeyboardInterrupt:
      pass
    finally:
        if URL_FILE.exists():
            URL_FILE.unlink()
        server.shutdown()
        server.server_close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
