from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from rag_core import answer, build_index, load_index


HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8765"))
RAG_PROFILE = os.getenv("RAG_PROFILE", "public").lower()


HTML = """<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Metagri AI案内Bot</title>
  <style>
    :root { color-scheme: light; --green:#2D6A4F; --yellow:#F4D35E; --ink:#1d2520; --line:#d8e0da; }
    body { margin:0; font-family: system-ui, -apple-system, "Segoe UI", sans-serif; color:var(--ink); background:#f7faf8; }
    header { background:var(--green); color:white; padding:18px 22px; }
    h1 { margin:0; font-size:20px; letter-spacing:0; }
    main { max-width:980px; margin:0 auto; padding:20px; }
    form { display:grid; grid-template-columns:1fr auto; gap:10px; margin-bottom:18px; }
    input { font-size:16px; padding:13px 14px; border:1px solid var(--line); border-radius:6px; }
    button { border:0; background:var(--green); color:white; padding:0 18px; border-radius:6px; font-weight:700; cursor:pointer; }
    .faq { margin:0 0 18px; }
    .faq h2 { margin:0 0 10px; font-size:15px; }
    .faq-list { display:flex; flex-wrap:wrap; gap:8px; }
    .faq-button { border:1px solid var(--line); background:white; color:var(--ink); padding:8px 11px; border-radius:6px; font-size:13px; font-weight:600; }
    .faq-button:hover { border-color:var(--green); color:var(--green); }
    .panel { background:white; border:1px solid var(--line); border-radius:8px; padding:16px; margin:12px 0; }
    .question { font-weight:700; border-left:5px solid var(--yellow); padding-left:10px; }
    .answer { line-height:1.8; }
    .source-details { margin-top:14px; color:#526158; font-size:13px; }
    .source-details summary { cursor:pointer; font-weight:700; }
    .sources { margin:8px 0 0; padding-left:22px; }
    .sources li { margin:5px 0; }
    .empty { color:#526158; }
  </style>
</head>
<body>
  <header><h1>Metagri AI案内Bot</h1></header>
  <main>
    <form id="chat-form">
      <input id="question" autocomplete="off" placeholder="例: Metagri研究所の現在の重点プロジェクトは？">
      <button type="submit">質問</button>
    </form>
    <section class="faq" aria-labelledby="faq-title">
      <h2 id="faq-title">よくある質問</h2>
      <div class="faq-list">
        <button type="button" class="faq-button">Metagri研究所とは？</button>
        <button type="button" class="faq-button">Metagri研究所の活動に参加したい</button>
        <button type="button" class="faq-button">MLTTを集めたい</button>
        <button type="button" class="faq-button">MLTTとMLTGの違いは？</button>
        <button type="button" class="faq-button">Metagri研究所の主な取り組みは？</button>
        <button type="button" class="faq-button">農業AI通信とは？</button>
        <button type="button" class="faq-button">白井市PR動画コンテストとは？</button>
        <button type="button" class="faq-button">未来の農業シミュレーターとは？</button>
      </div>
    </section>
    <div id="messages" class="empty">公開情報にもとづいて回答します。確認できない内容は、その旨を返します。</div>
  </main>
  <script>
    const form = document.querySelector("#chat-form");
    const input = document.querySelector("#question");
    const messages = document.querySelector("#messages");

    document.querySelectorAll(".faq-button").forEach((button) => {
      button.addEventListener("click", () => {
        input.value = button.textContent.trim();
        form.requestSubmit();
      });
    });

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const question = input.value.trim();
      if (!question) return;
      messages.classList.remove("empty");
      messages.insertAdjacentHTML("afterbegin", `<div class="panel question">${escapeHtml(question)}</div>`);
      input.value = "";
      const pending = document.createElement("div");
      pending.className = "panel";
      pending.textContent = "検索中...";
      messages.prepend(pending);
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({question})
      });
      const payload = await response.json();
      pending.innerHTML = render(payload);
    });

    function render(payload) {
      const body = escapeHtml(payload.answer).replaceAll("\\n", "<br>");
      const sources = (payload.evidence || []).map(item => (
        `<li><strong>${escapeHtml(item.file_name)}:${item.line}</strong> ${escapeHtml(item.heading || "")}</li>`
      )).join("");
      const sourceBlock = sources
        ? `<details class="source-details"><summary>参照元（${payload.evidence.length}件）</summary><ul class="sources">${sources}</ul></details>`
        : "";
      return `<div class="answer">${body}</div>${sourceBlock}`;
    }
    function escapeHtml(value) {
      return value.replace(/[&<>"']/g, char => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#039;" }[char]));
    }
  </script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/rebuild":
            index = build_index()
            self.send_json({"ok": True, "chunk_count": index["chunk_count"]})
            return
        if parsed.path != "/":
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(HTML.encode("utf-8"))

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/chat":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        payload = json.loads(raw or "{}")
        question = str(payload.get("question", "")).strip()
        if not question:
            self.send_json({"answer": "質問を入力してください。", "evidence": []}, status=400)
            return
        self.send_json(answer(question))

    def send_json(self, payload: dict, status: int = 200) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args) -> None:
        return


def main() -> None:
    load_index()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Metagri RAG Chatbot ({RAG_PROFILE}): http://{HOST}:{PORT}")
    print("Rebuild index: http://127.0.0.1:8765/rebuild")
    server.serve_forever()


if __name__ == "__main__":
    main()
