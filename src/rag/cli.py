"""Linha de comando.

    python -m rag.cli "Qual o limite do Pix à noite?"
    python -m rag.cli --docs minha_pasta --busca bm25      # modo interativo
"""

from __future__ import annotations

import argparse
from pathlib import Path

from .assistant import Assistant

ROOT = Path(__file__).resolve().parents[2]


def show(answer) -> None:
    print(f"\n{answer.text}\n")
    for i, hit in enumerate(answer.hits, start=1):
        print(f"  [{i}] {hit.chunk.source}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Pergunte aos seus documentos")
    parser.add_argument("pergunta", nargs="?", help="sem pergunta, abre o modo interativo")
    parser.add_argument("--docs", type=Path, default=ROOT / "docs_exemplo")
    parser.add_argument("--busca", choices=["bm25", "tfidf_char", "hibrido"], default="hibrido")
    args = parser.parse_args()

    assistant = Assistant.from_folder(args.docs, retriever=args.busca)
    print(f"{len(assistant.chunks)} trechos indexados · busca: {args.busca} · "
          f"resposta: {assistant.generator.name}")
    if args.pergunta:
        show(assistant.ask(args.pergunta))
        return
    while True:
        try:
            question = input("Pergunta (Enter para sair): ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not question:
            break
        show(assistant.ask(question))


if __name__ == "__main__":
    main()
