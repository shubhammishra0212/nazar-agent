"""HTTP service on 127.0.0.1:8766 (contract section 5). Standard library only.

    GET  /health   {"ok":true,"llm":"installed"|"loaded"|"missing","busy":false,"version":"2.0.0"}
    POST /report   inspection log JSON -> statistics + 8D report

Every answer is JSON with Access-Control-Allow-Origin: * (the console page has origin null),
OPTIONS is answered, and nothing a client sends can crash the service: errors come back as
{"ok":false,"error":"..."} with HTTP 200.

    python -m nazar_agent.service [--port 8766] [--no-preload]
"""
import argparse
import datetime
import json
import sys
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import VERSION, engine, llm

MAX_BODY = 32 * 1024 * 1024


def log(msg):
    print(f"[{datetime.datetime.now():%H:%M:%S}] {msg}", file=sys.stderr, flush=True)


def health():
    return {"ok": True, "llm": llm.status(), "busy": llm.busy(), "version": VERSION,
            "model": llm.NAME, "llm_error": llm.info()["error"]}


class Handler(BaseHTTPRequestHandler):
    server_version = f"nazar-agent/{VERSION}"

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Private-Network", "true")
        self.send_header("Access-Control-Max-Age", "600")

    def _json(self, obj, code=200):
        try:
            data = json.dumps(obj, ensure_ascii=False, allow_nan=False).encode("utf-8")
        except (TypeError, ValueError) as e:
            data = json.dumps({"ok": False, "error": f"could not encode answer: {e}"}).encode()
        try:
            self.send_response(code)
            self._cors()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_OPTIONS(self):
        try:
            self.send_response(204)
            self._cors()
            self.send_header("Content-Length", "0")
            self.end_headers()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        path = self.path.split("?", 1)[0].rstrip("/") or "/"
        try:
            if path in ("/health", "/"):
                return self._json(health())
            return self._json({"ok": False, "error": f"unknown path {path}; use GET /health or POST /report"})
        except Exception as e:
            return self._json({"ok": False, "error": f"{type(e).__name__}: {e}"})

    def do_POST(self):
        path = self.path.split("?", 1)[0].rstrip("/")
        try:
            if path != "/report":
                return self._json({"ok": False, "error": f"unknown path {path}; use POST /report"})
            try:
                size = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                size = -1
            if size <= 0:
                return self._json({"ok": False, "error": "empty body: send the inspection log as JSON"})
            if size > MAX_BODY:
                return self._json({"ok": False, "error": f"body too large ({size} bytes)"})
            raw = self.rfile.read(size)
            try:
                req = json.loads(raw.decode("utf-8-sig"))
            except (UnicodeDecodeError, json.JSONDecodeError) as e:
                return self._json({"ok": False, "error": f"body is not valid JSON: {e}"})
            n = len(req.get("inspections") or []) if isinstance(req, dict) else 0
            log(f"report: {n} rows, lang={req.get('lang', 'en') if isinstance(req, dict) else '?'}, "
                f"use_llm={req.get('use_llm', True) if isinstance(req, dict) else '?'}")
            out = engine.build(req)
            if out.get("ok"):
                st = out.get("stats", {})
                log(f"  -> {st.get('n')} used, cause={st.get('cause')}, writer={out.get('writer')}, "
                    f"{out.get('ms')} ms" + (f" ({out['note']})" if out.get("note") else ""))
            return self._json(out)
        except Exception as e:
            traceback.print_exc()
            return self._json({"ok": False, "error": f"{type(e).__name__}: {e}"})

    def log_message(self, fmt, *args):     # request lines are logged by do_POST; keep the console quiet
        pass


def main(argv=None):
    ap = argparse.ArgumentParser(description="NAZAR root-cause agent service")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8766)
    ap.add_argument("--no-preload", action="store_true", help="load the LLM on the first report, not at start")
    a = ap.parse_args(argv)
    try:
        srv = ThreadingHTTPServer((a.host, a.port), Handler)
    except OSError as e:
        log(f"cannot listen on {a.host}:{a.port}: {e} (is the agent already running? lsof -i :{a.port})")
        return 1
    srv.daemon_threads = True
    log(f"NAZAR agent {VERSION} on http://{a.host}:{a.port}  LLM: {llm.status()} ({llm.LLM_DIR})")
    if not a.no_preload and llm.status() == "installed":
        log("loading the local LLM in the background ...")
        llm.preload()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        log("stopped")
    finally:
        srv.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
