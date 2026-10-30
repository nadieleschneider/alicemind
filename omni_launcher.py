import importlib.util
import hmac
import os
import secrets
import socket
import subprocess
import sys
import threading
import time
import tkinter as tk
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tkinter import ttk
from urllib.error import URLError
from urllib.request import urlopen


APP_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
APP_DATA = Path(os.getenv("LOCALAPPDATA", Path.home())) / "Omni"
APP_DATA.mkdir(parents=True, exist_ok=True)


def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
        server_socket.bind(("127.0.0.1", 0))
        return server_socket.getsockname()[1]


def run_streamlit_server(port):
    app_path = APP_ROOT / "app.py"
    if not app_path.is_file():
        raise FileNotFoundError(
            f"Arquivo do AliceMind não encontrado: {app_path}"
        )

    os.environ["STREAMLIT_GLOBAL_DEVELOPMENT_MODE"] = "false"
    from streamlit.web import cli

    sys.argv = [
        "streamlit",
        "run",
        str(app_path),
        "--server.address=127.0.0.1",
        f"--server.port={port}",
        "--server.headless=true",
        "--server.fileWatcherType=none",
        "--browser.gatherUsageStats=false",
    ]
    cli.main()


def make_control_server(token, on_shutdown):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path != "/shutdown":
                self.send_error(404)
                return

            authorization = self.headers.get("Authorization", "")
            supplied_token = authorization.removeprefix("Bearer ").strip()
            if not hmac.compare_digest(supplied_token, token):
                self.send_error(403)
                return

            self.send_response(202)
            self.send_header("Content-Length", "0")
            self.end_headers()
            threading.Thread(target=on_shutdown, daemon=True).start()

        def log_message(self, _format, *_args):
            return

    return ThreadingHTTPServer(("127.0.0.1", 0), Handler)


class OmniLauncher:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AliceMind")
        self.root.geometry("390x255")
        self.root.minsize(360, 240)
        self.root.protocol("WM_DELETE_WINDOW", self.shutdown)

        self.port = find_free_port()
        self.url = f"http://127.0.0.1:{self.port}"
        self.token = secrets.token_urlsafe(32)
        self.server_process = None
        self.shutting_down = False
        self.log_file = (APP_DATA / "omni-server.log").open(
            "a", encoding="utf-8"
        )
        self.control_server = make_control_server(
            self.token,
            lambda: self.root.after(0, self.shutdown),
        )
        self.control_thread = threading.Thread(
            target=self.control_server.serve_forever,
            daemon=True,
        )
        self.control_thread.start()

        style = ttk.Style(self.root)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"))
        style.configure("Body.TLabel", font=("Segoe UI", 10))
        style.configure("Status.TLabel", font=("Segoe UI", 10))

        container = ttk.Frame(self.root, padding=22)
        container.pack(fill="both", expand=True)
        ttk.Label(container, text="AliceMind", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            container,
            text="Seu assistente pessoal está iniciando.",
            style="Body.TLabel",
        ).pack(anchor="w", pady=(6, 14))

        self.status = tk.StringVar(value="Iniciando o servidor local...")
        ttk.Label(
            container,
            textvariable=self.status,
            style="Status.TLabel",
            wraplength=330,
        ).pack(anchor="w", pady=(0, 14))

        button_row = ttk.Frame(container)
        button_row.pack(fill="x", side="bottom")
        self.open_button = ttk.Button(
            button_row,
            text="Abrir AliceMind",
            command=self.open_browser,
            state="disabled",
        )
        self.open_button.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(
            button_row,
            text="Encerrar AliceMind",
            command=self.shutdown,
        ).pack(side="left", fill="x", expand=True, padx=(6, 0))

        self.start_server()
        self.root.mainloop()

    def server_command(self):
        if getattr(sys, "frozen", False):
            return [sys.executable, "--omni-server", str(self.port)]
        return [
            sys.executable,
            str(Path(__file__).resolve()),
            "--omni-server",
            str(self.port),
        ]

    def start_server(self):
        environment = os.environ.copy()
        environment["OMNI_MEMORY_DIR"] = str(APP_DATA / "memory")
        project_root = (
            APP_ROOT
            if not getattr(sys, "frozen", False)
            else APP_DATA / "workspace"
        )
        project_root.mkdir(parents=True, exist_ok=True)
        environment["OMNI_PROJECT_DIR"] = str(project_root)
        environment["OMNI_DESKTOP_CONTROL_URL"] = (
            f"http://127.0.0.1:{self.control_server.server_port}/shutdown"
        )
        environment["OMNI_DESKTOP_CONTROL_TOKEN"] = self.token
        environment["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
        creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        self.server_process = subprocess.Popen(
            self.server_command(),
            cwd=APP_ROOT,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=self.log_file,
            stderr=subprocess.STDOUT,
            creationflags=creation_flags,
        )
        threading.Thread(target=self.wait_until_ready, daemon=True).start()

    def wait_until_ready(self):
        health_url = f"{self.url}/_stcore/health"
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            if self.shutting_down:
                return
            if self.server_process and self.server_process.poll() is not None:
                self.root.after(
                    0,
                    lambda: self.status.set(
                        "Não foi possível iniciar o AliceMind. "
                        f"Consulte o log em {APP_DATA / 'omni-server.log'}."
                    ),
                )
                return
            try:
                with urlopen(health_url, timeout=1) as response:
                    if response.status == 200:
                        self.root.after(0, self.server_ready)
                        return
            except (OSError, URLError):
                time.sleep(0.5)

        if not self.shutting_down:
            self.root.after(
                0,
                lambda: self.status.set(
                    "O AliceMind demorou demais para iniciar. "
                    f"Consulte o log em {APP_DATA / 'omni-server.log'}."
                ),
            )

    def server_ready(self):
        if self.shutting_down:
            return
        self.status.set("AliceMind pronto. A página será aberta no navegador.")
        self.open_button.configure(state="normal")
        self.open_browser()
        self.root.after(900, self.root.iconify)

    def open_browser(self):
        if not self.shutting_down:
            webbrowser.open(self.url, new=2)

    def shutdown(self):
        if self.shutting_down:
            return
        self.shutting_down = True
        self.status.set("Encerrando o servidor local...")
        process = self.server_process
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

        self.control_server.shutdown()
        self.control_server.server_close()
        self.log_file.close()
        self.root.destroy()


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "--self-test":
        required_files = (
            APP_ROOT / "app.py",
            APP_ROOT / "agent_core.py",
            APP_ROOT / "agent_executor.py",
        )
        missing_files = [str(path) for path in required_files if not path.is_file()]
        missing_modules = [
            name
            for name in (
                "streamlit",
                "requests",
                "pypdf",
                "reportlab",
                "resume_pdf",
            )
            if importlib.util.find_spec(name) is None
        ]
        if missing_files or missing_modules:
            raise RuntimeError(
                f"Recursos ausentes: {missing_files}; módulos ausentes: {missing_modules}"
            )
        return
    if len(sys.argv) >= 3 and sys.argv[1] == "--omni-server":
        run_streamlit_server(int(sys.argv[2]))
        return
    OmniLauncher()


if __name__ == "__main__":
    main()
