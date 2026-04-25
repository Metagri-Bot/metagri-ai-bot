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
    if "インターン" in question:
        return {
            "answer": "Metagri研究所では、学生インターンがコミュニティ運営や情報発信、農家・関係者へのインタビュー、SNS、勉強会などを担いながら、農業×新技術の現場を実践的に学ぶ体制があります。\n\n主な取り組みは次の通りです。\n\n- Discordコミュニティの運営補助。\n- 農家インタビューや関係者ヒアリングを通じた、農業現場の課題整理。\n- SNS投稿、記事化、音声配信、勉強会などの発信・共有活動。\n- 生成AI、web3、メタバースなどを農業テーマの実プロジェクトで学ぶ活動。\n\n個別インターンの氏名、所属、評価、稼働状況などは公開版では回答しません。募集状況や参加条件は変わるため、最新情報は公式サイト・Discord・運営からの案内を確認してください。",
            "confidence": "high",
            "evidence": [{"file_name": "metagri_intern_public.md", "heading": "Metagri研究所 インターン活動 公開用サマリー", "line": 1}],
            "results": [],
        }
    if "metagri" in normalized and any(term in question for term in ("歴史", "軌跡", "沿革", "これまで", "歩み", "あゆみ")):
        return {
            "answer": "Metagri研究所は、2022年3月に5名で始まり、2026年時点で1,300名規模のコミュニティに成長してきました。\n\n- 2022年3月: 当初5名でスタート。毎週日曜の定例MTGを継続。\n- 2022年4月以降: 農業NFT発行を開始（スイカ、トマト、シャインマスカット、いちご、マンゴー、柑橘の接ぎ木など）。\n- 立ち上げ初期から: 貢献を可視化するMLTTを発行し、トークンエコノミーを整備。\n- 2026年3月: 4年間DAOレポートを無料公開し、続くDAOの設計原則と成長実績を整理。\n- 2026年: 白井市PR動画コンテスト、農業AIハッカソン、未来の農業シミュレーター、農業AI通信などを並行展開。\n\n主なターニングポイントは、農業NFT発行の開始、MLTT / MLTGによるトークンエコノミー導入、4年間DAOレポート公開、自治体連携の本格化です。",
            "confidence": "high",
            "evidence": [{"file_name": "metagri_history_public.md", "heading": "Metagri研究所 軌跡・歴史 公開用サマリー", "line": 1}],
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
