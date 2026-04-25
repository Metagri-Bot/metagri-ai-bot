from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from rag_core import answer  # noqa: E402


def public_fast_answer(question: str) -> dict | None:
    normalized = question.lower()
    if any(term in question for term in ("売上", "契約", "予算", "資金源", "ライセンス", "アカウント", "請求書", "銀行", "パスワード", "認証")):
        return {
            "answer": "手元の公開情報では確認できません。Metagri研究所の公開版AI案内Botでは、売上・契約・予算・資金源・ライセンス・アカウント情報など、公開済みページで確認できない内部情報には回答しません。\n\n公開済みの取り組みや公式ページにある内容について質問してください。",
            "confidence": "high",
            "evidence": [{"file_name": "public_refusal_policy.md", "heading": "公開版チャットボット 非回答方針", "line": 1}],
            "results": [],
        }
    if "metagri" in normalized and any(term in question for term in ("取り組み", "プロジェクト", "重点", "進行中")):
        return {
            "answer": "Metagri研究所の主な取り組みは、以下のように整理できます。\n\n- 農業AI通信: 農家向けにAI活用の入口を届けるWebメディア。\n- 白井市PR動画コンテスト: 動画生成AIを活用した自治体連携型の地域PR施策。\n- MLTT / MLTG: コミュニティ貢献をトークンやNFT特典に接続する仕組み。\n- 未来の農業シミュレーター: Roblox上で農業体験を提供するメタバース施策。\n- 農業AIハッカソン: 農家や地域課題を起点に、生成AIでプロトタイプを作る共創プログラム。\n- 4年間DAOレポート: コミュニティ継続の実績をデータで示す取り組み。",
            "confidence": "high",
            "evidence": [{"file_name": "metagri_overview_public.md", "heading": "Metagri研究所 公開用サマリー", "line": 1}],
            "results": [],
        }
    if "metagri" in normalized and ("とは" in question or "何" in question):
        return {
            "answer": "Metagri研究所は、株式会社農情人が運営する、農業×新技術の実験コミュニティです。\n\n- Discordを中心に、農業とweb3、生成AI、メタバースを組み合わせた取り組みを行っています。\n- コンセプトは「Meta（超越）× Agriculture（農業）」です。\n- 農業の固定観念をテクノロジーで超越し、新しい農業の関わり方を作ることを目指しています。",
            "confidence": "high",
            "evidence": [{"file_name": "metagri_overview_public.md", "heading": "Metagri研究所 公開用サマリー", "line": 1}],
            "results": [],
        }
    if "milk monster" in normalized or "ミルクモンスター" in question or "cwbj" in normalized:
        return {
            "answer": "手元の公開情報では確認できません。Metagri研究所の公開版AI案内Botでは、公式サイトや公開記事で確認できる内容に限って回答します。\n\n公開済みページがある取り組みについて質問するか、公式発表後にあらためて確認してください。",
            "confidence": "high",
            "evidence": [{"file_name": "public_refusal_policy.md", "heading": "公開版チャットボット 非回答方針", "line": 1}],
            "results": [],
        }
    return None


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
