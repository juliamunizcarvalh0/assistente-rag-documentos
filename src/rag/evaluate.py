"""Avaliação objetiva da busca sobre as leis.

Cada pergunta do conjunto de avaliação foi escrita como uma pessoa comum
perguntaria ("Posso desistir de uma compra que fiz pela internet?") e tem a
resposta conhecida: o artigo certo e o trecho exato que responde.

Mede:
1. **Busca**: o artigo certo aparece entre os primeiros resultados?
   Métricas: Hit@1, Hit@3, Hit@5 e MRR, para cada estratégia e para cada lei.
2. **Recusa** (modo sem IA): o assistente recusa perguntas fora do escopo?

Uso:
    python -m rag.evaluate            # só a busca, sem IA
    python -m rag.evaluate --gemini   # inclui a reescrita da pergunta pelo Gemini
                                      # (precisa de GEMINI_API_KEY; usa ~60 chamadas)
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .assistant import Assistant
from .generate import ExtractiveGenerator
from .ingest import chunk_sections, find_documents, load_documents
from .retrievers import build_retrievers
from .text import strip_accents

ROOT = Path(__file__).resolve().parents[2]


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", strip_accents(text.lower().replace("*", ""))).strip()


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def is_relevant(chunk, item: dict) -> bool:
    return chunk.label == item["artigo"] and _norm(item["evidencia"]) in _norm(chunk.text)


def first_relevant_rank(retriever, item: dict, k: int = 5) -> int | None:
    results = retriever.search(item["pergunta"], k)
    return next((i for i, h in enumerate(results, 1) if is_relevant(h.chunk, item)), None)


def metrics(ranks: list[int | None]) -> dict[str, float]:
    n = len(ranks)
    return {
        "hit@1": sum(r is not None and r <= 1 for r in ranks) / n,
        "hit@3": sum(r is not None and r <= 3 for r in ranks) / n,
        "hit@5": sum(r is not None for r in ranks) / n,
        "mrr": sum(1 / r for r in ranks if r) / n,
    }


def evaluate_set(retrievers: dict, questions: list[dict]) -> dict:
    ranks = {name: [first_relevant_rank(r, q) for q in questions]
             for name, r in retrievers.items()}
    by_law = {}
    for law in sorted({q["artigo"].split(",")[0] for q in questions}):
        idx = [i for i, q in enumerate(questions) if q["artigo"].startswith(law + ",")]
        by_law[law] = {"n": len(idx), **metrics([ranks[BEST][i] for i in idx])}
    best = retrievers[BEST]
    return {
        "n": len(questions),
        "busca": {name: metrics(r) for name, r in ranks.items()},
        "por_lei": by_law,
        "falhas": [
            {"pergunta": q["pergunta"], "esperado": q["artigo"],
             "encontrado": [h.chunk.label for h in best.search(q["pergunta"], 3)]}
            for q, r in zip(questions, ranks[BEST], strict=True) if not r or r > 3
        ],
    }


BEST = "hibrido_glossario"


class RewriteRetriever:
    """Busca como o app faz com IA: pergunta original + reescrita do Gemini, fundidas."""

    name = "gemini_reescrita"

    def __init__(self, assistant: Assistant):
        self.assistant = assistant

    def search(self, query: str, k: int = 5):
        rewritten = self.assistant._rewrite(query, [])
        return self.assistant._fused_search(query, rewritten, None)[:k]


def run(laws: Path = ROOT / "leis", eval_dir: Path = ROOT / "eval",
        with_gemini: bool = False) -> dict:
    sets = {
        "desenvolvimento": load_jsonl(eval_dir / "perguntas.jsonl"),
        "teste": load_jsonl(eval_dir / "perguntas_teste.jsonl"),
    }
    out_of_scope = load_jsonl(eval_dir / "fora_do_escopo.jsonl")
    chunks = chunk_sections(load_documents(find_documents(laws)))

    for questions in sets.values():
        missing = [q["pergunta"] for q in questions if not any(is_relevant(c, q) for c in chunks)]
        if missing:
            raise ValueError(f"Trecho esperado não encontrado em nenhum artigo: {missing}")

    retrievers = build_retrievers(chunks)
    if with_gemini:
        from .generate import GeminiGenerator

        llm_assistant = Assistant(chunks, generator=GeminiGenerator(), k=5)
        retrievers["gemini_reescrita"] = RewriteRetriever(llm_assistant)
    assistant = Assistant(chunks, generator=ExtractiveGenerator())
    refusals = [assistant.ask(q["pergunta"]) for q in out_of_scope]
    return {
        "n_trechos": len(chunks),
        "trechos_por_lei": {d: sum(c.document == d for c in chunks)
                            for d in sorted({c.document for c in chunks})},
        "conjuntos": {name: evaluate_set(retrievers, qs) for name, qs in sets.items()},
        "recusou_fora_do_escopo": sum(not a.answered for a in refusals) / len(refusals),
    }


def to_markdown(r: dict) -> str:
    pct = lambda v: f"{v:.0%}"  # noqa: E731
    per_law = ", ".join(f"{d}: {n}" for d, n in r["trechos_por_lei"].items())
    dev, test = r["conjuntos"]["desenvolvimento"], r["conjuntos"]["teste"]
    lines = [
        "# Relatório de avaliação da busca",
        "",
        f"Índice: {r['n_trechos']} trechos ({per_law}). Perguntas escritas em linguagem do dia a "
        "dia, cada uma com o artigo e o trecho exato que a responde.",
        "",
        f"- **Desenvolvimento** ({dev['n']} perguntas): usado para analisar os erros e "
        "melhorar a busca.",
        f"- **Teste** ({test['n']} perguntas, outros assuntos): escrito à parte e **não** usado "
        "para ajustar nada. Mostra se as melhorias generalizam.",
        "",
        "Resultados **sem IA**. No app, o Gemini ainda reescreve a pergunta antes da busca.",
        "",
        "## Hit@3 e MRR por estratégia",
        "",
        "| Estratégia | Hit@3 (desenv.) | MRR (desenv.) | Hit@3 (teste) | MRR (teste) |",
        "|---|---|---|---|---|",
    ]
    for name in dev["busca"]:
        d, t = dev["busca"][name], test["busca"][name]
        lines.append(f"| {name} | {pct(d['hit@3'])} | {d['mrr']:.3f} | "
                     f"{pct(t['hit@3'])} | {t['mrr']:.3f} |")
    lines += ["", f"## Por lei ({BEST}, conjunto de teste)", "",
              "| Lei | Perguntas | Hit@1 | Hit@3 | MRR |", "|---|---|---|---|---|"]
    for law, m in test["por_lei"].items():
        lines.append(f"| {law} | {m['n']} | {pct(m['hit@1'])} | {pct(m['hit@3'])} | "
                     f"{m['mrr']:.3f} |")
    lines += ["", f"Perguntas fora do escopo recusadas (modo sem IA): "
              f"**{pct(r['recusou_fora_do_escopo'])}**", ""]
    for title, data in (("desenvolvimento", dev), ("teste", test)):
        lines += [f"## Erros no conjunto de {title} (artigo certo fora do top 3)", ""]
        lines += [f"- {f['pergunta']} — esperado **{f['esperado']}**, veio "
                  f"{', '.join(f['encontrado']) or 'nada'}" for f in data["falhas"]] or ["- nenhum"]
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Avaliação da busca")
    parser.add_argument("--gemini", action="store_true",
                        help="inclui a reescrita da pergunta pelo Gemini")
    args = parser.parse_args()
    results = run(with_gemini=args.gemini)
    report = to_markdown(results)
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "avaliacao.md").write_text(report, encoding="utf-8")
    (ROOT / "reports" / "avaliacao.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
