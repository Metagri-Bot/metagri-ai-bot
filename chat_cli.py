from __future__ import annotations

import argparse
import sys

from rag_core import answer


def format_cli(payload: dict) -> str:
    text = payload["answer"]
    evidence = payload.get("evidence") or []
    if evidence:
        sources = []
        seen = set()
        for item in evidence:
            label = f"{item['file_name']}:{item['line']} {item.get('heading') or ''}".strip()
            if label in seen:
                continue
            seen.add(label)
            sources.append(f"- {label}")
        text += "\n\n参照元:\n" + "\n".join(sources)
    return text


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Metagri RAG chatbot CLI")
    parser.add_argument("question", nargs="*", help="質問文")
    args = parser.parse_args()

    question = " ".join(args.question).strip()
    if question:
        print(format_cli(answer(question)))
        return

    print("Metagri RAG Chatbot CLI。終了するには exit と入力してください。")
    while True:
        question = input("\n質問> ").strip()
        if question.lower() in {"exit", "quit", "q"}:
            break
        if not question:
            continue
        print("\n" + format_cli(answer(question)))


if __name__ == "__main__":
    main()
