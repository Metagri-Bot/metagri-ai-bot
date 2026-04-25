from __future__ import annotations

import glob
import html
import json
import math
import os
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parent
RAG_PROFILE = os.getenv("RAG_PROFILE", "public").lower()
DATA_DIR = Path(os.getenv("RAG_DATA_DIR", ROOT / ("data_public" if RAG_PROFILE == "public" else "data")))
INDEX_PATH = DATA_DIR / "index.json"
SOURCES_PATH = Path(os.getenv("RAG_SOURCES_FILE", ROOT / ("sources_public.json" if RAG_PROFILE == "public" else "sources.json")))
CANONICAL_QA_PATH = Path(os.getenv("RAG_QA_FILE", ROOT / ("canonical_qa_public.json" if RAG_PROFILE == "public" else "canonical_qa.json")))
UNANSWERED_LOG_PATH = DATA_DIR / "unanswered_questions.jsonl"


JAPANESE_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")
WORD_RE = re.compile(r"[a-zA-Z0-9_]{2,}|[\u3040-\u30ff\u3400-\u9fff]{2,}")
SENTENCE_RE = re.compile(r"(?<=[。！？!?])\s+|\n+")
STOP_TERMS = {
    "とは",
    "です",
    "ます",
    "して",
    "から",
    "こと",
    "もの",
    "ため",
    "これ",
    "それ",
    "どの",
    "なに",
    "何で",
    "何です",
    "概要",
    "違い",
    "教えて",
    "ください",
    "について",
}


@dataclass
class SearchResult:
    score: float
    chunk: dict


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    return text.lower()


def tokenize(text: str) -> list[str]:
    normalized = normalize(text)
    words = WORD_RE.findall(normalized)
    compact_jp = "".join(ch for ch in normalized if JAPANESE_RE.match(ch))
    grams: list[str] = []
    for size in (2, 3):
        grams.extend(compact_jp[i : i + size] for i in range(max(0, len(compact_jp) - size + 1)))
    return words + grams


def tokenize_query(text: str) -> list[str]:
    tokens = tokenize(text)
    filtered = []
    for token in tokens:
        if token in STOP_TERMS:
            continue
        if any(stop in token for stop in STOP_TERMS):
            continue
        filtered.append(token)
    return filtered


def clean_markdown(text: str) -> str:
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def iter_local_files(sources_path: Path = SOURCES_PATH) -> Iterable[tuple[Path, dict]]:
    manifest = json.loads(sources_path.read_text(encoding="utf-8"))
    for source in manifest["trusted_local_sources"]:
        if source.get("enabled") is False:
            continue
        pattern = source["path"]
        paths = glob.glob(pattern) if "*" in pattern else [pattern]
        for raw_path in paths:
            path = Path(raw_path)
            if not path.exists() or path.suffix.lower() not in {".md", ".txt"}:
                continue
            # Avoid known sensitive export by default. Switch to explicit allowlist for production.
            lowered = path.name.lower()
            if "password" in lowered or "パスワード" in lowered:
                continue
            yield path, source


def heading_before(lines: list[str], index: int) -> str:
    for i in range(index, -1, -1):
        line = lines[i].strip()
        if line.startswith("#"):
            return line.lstrip("#").strip()
    return ""


def chunk_file(path: Path, source: dict, chunk_size: int = 1600, overlap: int = 220) -> list[dict]:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    lines = raw.splitlines()
    chunks: list[dict] = []
    current = []
    current_len = 0
    start_line = 1

    for line_no, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue
        if not current:
            start_line = line_no
        current.append(stripped)
        current_len += len(stripped)
        if current_len >= chunk_size:
            text = clean_markdown("\n".join(current))
            if text:
                chunks.append(
                    make_chunk(path, source, text, start_line, line_no, heading_before(lines, line_no - 1))
                )
            tail = "\n".join(current)[-overlap:]
            current = [tail] if tail else []
            current_len = len(tail)
            start_line = max(1, line_no - 5)

    if current:
        text = clean_markdown("\n".join(current))
        if text:
            chunks.append(make_chunk(path, source, text, start_line, len(lines), heading_before(lines, len(lines) - 1)))
    return chunks


def make_chunk(path: Path, source: dict, text: str, start_line: int, end_line: int, heading: str) -> dict:
    rel_name = path.name
    token_counts = Counter(tokenize(text))
    return {
        "id": f"{path.as_posix()}:{start_line}",
        "source_name": source["name"],
        "source_path": path.as_posix(),
        "file_name": rel_name,
        "heading": heading,
        "start_line": start_line,
        "end_line": end_line,
        "priority": source.get("priority", 3),
        "text": text,
        "tokens": dict(token_counts),
    }


def build_index() -> dict:
    DATA_DIR.mkdir(exist_ok=True)
    chunks: list[dict] = []
    for path, source in iter_local_files():
        chunks.extend(chunk_file(path, source))

    doc_freq: dict[str, int] = defaultdict(int)
    for chunk in chunks:
        for token in chunk["tokens"]:
            doc_freq[token] += 1

    index = {
        "version": 1,
        "source_manifest": SOURCES_PATH.as_posix(),
        "chunk_count": len(chunks),
        "chunks": chunks,
        "doc_freq": dict(doc_freq),
    }
    INDEX_PATH.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    return index


def load_index() -> dict:
    if not INDEX_PATH.exists():
        return build_index()
    return json.loads(INDEX_PATH.read_text(encoding="utf-8"))


def search(query: str, top_k: int = 6, index: dict | None = None) -> list[SearchResult]:
    index = index or load_index()
    q_tokens = Counter(tokenize_query(query))
    if not q_tokens:
        return []

    total_docs = max(1, index["chunk_count"])
    results: list[SearchResult] = []
    for chunk in index["chunks"]:
        score = 0.0
        chunk_tokens = chunk["tokens"]
        for token, q_count in q_tokens.items():
            tf = chunk_tokens.get(token, 0)
            if not tf:
                continue
            df = index["doc_freq"].get(token, 1)
            idf = math.log((total_docs + 1) / (df + 0.5)) + 1
            score += (1 + math.log(tf)) * idf * min(q_count, 3)
        heading_blob = normalize(f"{chunk.get('file_name', '')} {chunk.get('heading', '')}")
        for term in important_query_terms(query):
            if term in heading_blob:
                score += 8.0
        if "metagri" in normalize(query) and ("とは" in query or "何" in query) and chunk.get("file_name") == "company.md":
            score = score * 5.0 + 30.0
        score = score / max(1, chunk.get("priority", 3))
        if score > 0:
            results.append(SearchResult(score=score, chunk=chunk))

    results.sort(key=lambda item: item.score, reverse=True)
    return results[:top_k]


def important_query_terms(query: str) -> list[str]:
    terms = [
        term
        for term in WORD_RE.findall(normalize(query))
        if len(term) >= 2 and term not in STOP_TERMS and not any(term.endswith(stop) for stop in STOP_TERMS)
    ]
    return sorted(set(terms), key=len, reverse=True)[:12]


def extract_evidence_sentences(query: str, chunks: list[dict], max_sentences: int = 5) -> list[dict]:
    terms = important_query_terms(query)
    core_terms = [term for term in terms if len(term) >= 3 or re.search(r"[a-z0-9]", term)]
    evidence = []
    seen = set()
    for chunk in chunks:
        sentences = [s.strip(" ・-*　") for s in SENTENCE_RE.split(chunk["text"]) if len(s.strip()) >= 25]
        ranked = []
        for sentence in sentences:
            if sentence.count("http") >= 1 and len(re.sub(r"https?://\S+", "", sentence).strip()) < 20:
                continue
            normalized = normalize(sentence)
            hit_count = sum(1 for term in terms if term in normalized)
            core_hit = not core_terms or any(term in normalized for term in core_terms)
            if not core_hit:
                continue
            if hit_count:
                quality = hit_count * 10
                if re.search(r"概要|コンセプト|形態|運営|現在|開始|目的|役割|正式名|活動|貢献|引き換え|コミュニティ", sentence):
                    quality += 6
                if "|" in sentence:
                    quality += 3
                if "URL" in sentence or "Twitter/X" in sentence or "OpenSea" in sentence:
                    quality -= 4
                quality += min(len(sentence), 160) / 160
                ranked.append((quality, sentence))
        if not ranked and sentences and not core_terms:
            ranked = [(0, sentences[0])]
        ranked.sort(key=lambda item: (item[0], len(item[1])), reverse=True)
        for _, sentence in ranked[:2]:
            sentence = format_evidence_sentence(sentence)
            key = normalize(sentence[:120])
            if key in seen:
                continue
            seen.add(key)
            evidence.append({"sentence": sentence, "chunk": chunk})
            break
        if len(evidence) >= max_sentences:
            break
    return evidence


def format_evidence_sentence(sentence: str, max_length: int = 180) -> str:
    sentence = re.sub(r"https?://\S+", "", sentence)
    sentence = re.sub(r"\*\*([^*]+)\*\*", r"\1", sentence)
    sentence = re.sub(r"`([^`]+)`", r"\1", sentence)
    if sentence.strip().startswith("|") and "|" in sentence:
        cells = [cell.strip() for cell in sentence.strip().strip("|").split("|") if cell.strip()]
        sentence = " / ".join(cells)
    sentence = re.sub(r"\s+", " ", sentence).strip(" -|")
    if len(sentence) > max_length:
        sentence = sentence[:max_length].rstrip() + "..."
    return sentence


def answer(query: str, top_k: int = 6) -> dict:
    canonical = canonical_answer(query)
    if canonical:
        return canonical

    results = search(query, top_k=top_k)
    if not results or results[0].score < 1.0:
        log_unanswered(query, "no_search_result")
        return {
            "answer": "手元のMetagri研究所ソースからは、十分な根拠を見つけられませんでした。質問を具体化するか、追加資料をRAGソースに入れてから再検索してください。",
            "confidence": "low",
            "evidence": [],
            "results": [],
        }

    chunks = [result.chunk for result in results]
    evidence = extract_evidence_sentences(query, chunks)
    if not evidence:
        log_unanswered(query, "no_clear_evidence")
        return {
            "answer": "関連しそうな資料は見つかりましたが、回答に使える明確な記述を抽出できませんでした。",
            "confidence": "low",
            "evidence": [],
            "results": serialize_results(results),
        }

    bullets = [f"- {item['sentence']}" for item in evidence]
    answer_text = "関連する記述を整理すると、次の通りです。\n\n"
    answer_text += "\n".join(bullets)
    return {
        "answer": answer_text,
        "confidence": "medium",
        "evidence": evidence_for_json(evidence),
        "results": serialize_results(results),
    }


def canonical_answer(query: str) -> dict | None:
    normalized = normalize(query)
    index = load_index()

    def find_chunk(file_name: str) -> dict | None:
        return next((chunk for chunk in index["chunks"] if chunk["file_name"] == file_name), None)

    def evidence_item(file_name: str, heading: str, text: str) -> dict | None:
        chunk = find_chunk(file_name)
        if not chunk:
            return None
        return {
            "text": text,
            "source": chunk["source_path"],
            "file_name": chunk["file_name"],
            "heading": heading,
            "line": chunk["start_line"],
        }

    file_answer = canonical_answer_from_file(query, find_chunk)
    if file_answer:
        return file_answer

    if "metagri" in normalized and ("取り組み" in query or "重点" in query or "進行中" in query or "プロジェクト" in query):
        evidence = [
            evidence_item("agri-ai-news.md", "農業AI通信", "農家向けAI活用メディア。診断・CTA導線の改善も進行中。"),
            evidence_item("shiroi-video-contest.md", "白井市PR動画コンテスト", "動画生成AIを活用した自治体連携型PRコンテスト。"),
            evidence_item("mltt-2026.md", "MLTT 2026", "貢献トークンと引き換えNFTによるトークンエコノミー刷新。"),
            evidence_item("milk-day-2026.md", "牛乳月間2026 / Milk Monster", "酪農・牛乳月間に向けた参加型企画とプロダクト実験。"),
            evidence_item("intern-operations.md", "インターン運営", "高校生・大学生インターンによる運営・記事・企画づくり。"),
            evidence_item("discord-community-ops.md", "Discord運用改善", "1,000人以上が参加するコミュニティの運用改善。"),
        ]
        evidence = [item for item in evidence if item]
        text = (
            "Metagri研究所の取り組みは、大きく6つに整理できます。\n\n"
            "- 農業AI通信: 農家向けにAI活用事例・実践ノウハウを発信するメディア運営。\n"
            "- 白井市PR動画コンテスト: 動画生成AIを使った自治体連携型の地域PR施策。\n"
            "- MLTT / MLTG 2026: コミュニティ貢献をトークンとNFT特典に接続する仕組み。\n"
            "- 牛乳月間2026 / Milk Monster: 酪農・牛乳消費をテーマにした参加型企画とプロダクト実験。\n"
            "- インターン運営: 学生インターンがDiscord運営、農家インタビュー、SNS、勉強会などを担う体制づくり。\n"
            "- Discord運用改善: Metagri研究所コミュニティの活性化、Bot、定例会議、テーマ別交流会の整備。\n\n"
            "つまり、メディア発信、コミュニティ運営、web3、AI、自治体連携、教育を組み合わせて、農業分野で小さな実証を積み上げている状態です。"
        )
        return {
            "answer": text,
            "confidence": "high",
            "evidence": evidence,
            "results": [],
        }

    if "metagri" in normalized and ("とは" in query or "何" in query):
        chunk = find_chunk("company.md")
        if not chunk:
            return None
        text = (
            "Metagri研究所は、株式会社農情人が運営する、Discordを中心としたコミュニティ型研究所です。\n\n"
            "- 2022年3月に開始し、2026年現在は1,300名以上が参加しています。\n"
            "- コンセプトは「Meta（超越）× Agriculture（農業）」で、農業の固定観念をテクノロジーで超越することを掲げています。\n"
            "- 主な活動領域は、web3 / NFT活用、生成AI活用、メタバースです。\n"
            "- 運営母体は株式会社農情人で、農業×新技術の実証実験や農家支援を進めています。"
        )
        return {
            "answer": text,
            "confidence": "high",
            "evidence": [
                {
                    "text": "Metagri研究所の基本情報、コンセプト、活動領域を参照。",
                    "source": chunk["source_path"],
                    "file_name": chunk["file_name"],
                    "heading": "会社・コミュニティ情報",
                    "line": chunk["start_line"],
                }
            ],
            "results": [],
        }

    if "mltt" in normalized and "mltg" in normalized and ("違い" in query or "とは" in query):
        chunk = find_chunk("mltt-2026.md")
        if not chunk:
            return None
        text = (
            "MLTTとMLTGの違いは、役割で整理できます。\n\n"
            "- MLTT（MetagriLabo Thanks Token）は、活動・貢献に応じて配布される感謝トークンです。\n"
            "- MLTG（MetagriLabo Thanks Gift）は、MLTTと引き換えるNFTで、特典の引換証として使われます。\n"
            "- 2026年度版では、書籍・グッズ・イベント参加・Vibe Coding個別メンタリング・新規企画立ち上げ支援などの交換先が整理されています。"
        )
        return {
            "answer": text,
            "confidence": "high",
            "evidence": [
                {
                    "text": "MLTTとMLTGの用語整理、交換NFT一覧を参照。",
                    "source": chunk["source_path"],
                    "file_name": chunk["file_name"],
                    "heading": "MLTT 2026 / トークンエコノミー刷新",
                    "line": chunk["start_line"],
                }
            ],
            "results": [],
        }

    if "農業ai通信" in normalized and ("課題" in query or "問題" in query or "改善" in query):
        chunk = find_chunk("agri-ai-news.md")
        if not chunk:
            return None
        text = (
            "農業AI通信の直近課題は、集客そのものよりも「診断・登録への導線」にあります。\n\n"
            "- 2026年4月時点で、diagnosis_complete が直近7日で0件になったことが緊急アラートとして記録されています。\n"
            "- CTA自体の表示は増えている一方、cta_click やキーイベントが落ちており、診断フォームや送信設定の確認が必要とされています。\n"
            "- 28日間GA4分析では、CTA到達率が20.7%に留まり、記事から診断・登録へ進む導線が弱いことが構造課題とされています。\n"
            "- 入口表記と実際の診断ボリュームにズレがあり、期待値調整も改善ポイントです。"
        )
        return {
            "answer": text,
            "confidence": "high",
            "evidence": [
                {
                    "text": "農業AI通信の2026年4月緊急アラート、CTA到達率、診断フォーム改善案を参照。",
                    "source": chunk["source_path"],
                    "file_name": chunk["file_name"],
                    "heading": "農業AI通信",
                    "line": chunk["start_line"],
                }
            ],
            "results": [],
        }

    if ("梶原" in query or "kamokobu" in normalized) and ("アンバサダー" in query or "企画" in query or "取り組み" in query):
        chunk = find_chunk("kajihara-ambassador.md")
        if not chunk:
            return None
        text = (
            "梶原さんのアンバサダー企画は、AI活用の成果を記事化するだけではなく、農業経営のデータ基盤づくりから継続運用までを伴走する取り組みです。\n\n"
            "- 実務実装: 品種別原価、KSAS日報、収量、資産などを見える化する基盤づくり。\n"
            "- AI設計: データをAIに渡し、経営判断の材料を出す「経営参謀」として育てる設計。\n"
            "- 情報発信: 試行錯誤の過程を農業AI通信の記事やセミナーとして連載化。\n"
            "- 現時点の重要課題は、売上データ統合、CSV化・要約などの軽量処理、判断履歴の運用、外部環境データの取り込みです。\n\n"
            "この企画の本質は、単発のAI活用事例紹介ではなく、AI活用を継続的に前進させる関係性と仕組みをつくることです。"
        )
        return {
            "answer": text,
            "confidence": "high",
            "evidence": [
                {
                    "text": "梶原さんの取り組みの3本柱、記事シリーズ進捗、現時点の重要課題を参照。",
                    "source": chunk["source_path"],
                    "file_name": chunk["file_name"],
                    "heading": "梶原さん × 農業AI通信メディアアンバサダー",
                    "line": chunk["start_line"],
                }
            ],
            "results": [],
        }

    return None


def canonical_answer_from_file(query: str, find_chunk) -> dict | None:
    if not CANONICAL_QA_PATH.exists():
        return None
    data = json.loads(CANONICAL_QA_PATH.read_text(encoding="utf-8"))
    normalized_query = normalize(query)
    scored_items = []
    for item in data.get("items", []):
        item_id = item.get("id", "")
        is_overview = item_id in {"metagri_overview", "metagri_overview_public"}
        is_projects = item_id in {"metagri_projects", "metagri_projects_public"}
        project_terms = ("取り組み", "プロジェクト", "重点", "進行中")
        if is_overview and any(term in query for term in project_terms):
            continue
        if is_overview and not ("とは" in query or "何" in query):
            continue
        if is_projects and not any(term in query for term in project_terms):
            continue
        keywords = item.get("keywords", [])
        hits = 0
        for keyword in keywords:
            normalized_keyword = normalize(keyword)
            if normalized_keyword in normalized_query:
                hits += 1
        if hits:
            single_hit_ids = {
                "milk_monster",
                "cwbj_collaboration",
                "dao_report",
                "future_farm_simulator",
                "ai_hackathon",
                "metagri_projects_public",
                "metagri_participation_public",
                "shiroi_public",
                "public_sensitive_info",
                "public_unconfirmed_project",
            }
            required_hits = 1 if item.get("id") in single_hit_ids else min(2, len(keywords))
            if hits < required_hits:
                continue
            scored_items.append((hits, len(keywords), item))
    if not scored_items:
        return None
    scored_items.sort(key=lambda row: (row[0], -row[1]), reverse=True)
    hits, keyword_count, item = scored_items[0]

    evidence = []
    for source in item.get("evidence", []):
        chunk = find_chunk(source["file_name"])
        if not chunk:
            continue
        evidence.append(
            {
                "text": source.get("text", item.get("title", "")),
                "source": chunk["source_path"],
                "file_name": chunk["file_name"],
                "heading": source.get("heading") or chunk.get("heading", ""),
                "line": chunk["start_line"],
            }
        )
    return {
        "answer": item["answer"],
        "confidence": "high",
        "evidence": evidence,
        "results": [],
    }


def log_unanswered(query: str, reason: str) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    record = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "reason": reason,
        "query": query,
    }
    with UNANSWERED_LOG_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")


def evidence_for_json(evidence: list[dict]) -> list[dict]:
    output = []
    for item in evidence:
        chunk = item["chunk"]
        output.append(
            {
                "text": item["sentence"],
                "source": chunk["source_path"],
                "file_name": chunk["file_name"],
                "heading": chunk.get("heading", ""),
                "line": chunk["start_line"],
            }
        )
    return output


def serialize_results(results: list[SearchResult]) -> list[dict]:
    return [
        {
            "score": round(result.score, 3),
            "file_name": result.chunk["file_name"],
            "heading": result.chunk.get("heading", ""),
            "source": result.chunk["source_path"],
            "line": result.chunk["start_line"],
            "preview": result.chunk["text"][:300],
        }
        for result in results
    ]


def render_html_answer(payload: dict) -> str:
    body = html.escape(payload["answer"]).replace("\n", "<br>")
    evidence = "".join(
        f"<li><strong>{html.escape(item['file_name'])}:{item['line']}</strong> "
        f"{html.escape(item.get('heading') or '')}</li>"
        for item in payload.get("evidence", [])
    )
    if not evidence:
        return f"<div class='answer'>{body}</div>"
    return f"<div class='answer'>{body}</div><details class='source-details'><summary>参照元（{len(payload.get('evidence', []))}件）</summary><ul class='sources'>{evidence}</ul></details>"
