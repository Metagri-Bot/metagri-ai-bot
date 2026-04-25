from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag_core import answer  # noqa: E402
from api.chat import public_fast_answer  # noqa: E402


class handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        payload = json.loads(raw or "{}")
        question = str(payload.get("question", "")).strip()
        if not question:
            self._send_json({"answer": "質問を入力してください。", "evidence": []}, status=400)
            return
        self._send_json(public_fast_answer(question) or answer(question))

    def do_GET(self) -> None:
        self._send_json({"ok": True, "message": "Metagri AI案内Bot API"})

    def _send_json(self, payload: dict, status: int = 200) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
