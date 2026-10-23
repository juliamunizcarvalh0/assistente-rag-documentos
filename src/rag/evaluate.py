"""Avaliação objetiva do assistente.

Mede:
1. **Busca**: para cada pergunta do conjunto de avaliação, o trecho certo
   (o que contém a evidência) aparece entre os primeiros resultados?
   Métricas: Hit@1, Hit@3, Hit@5 e MRR, para cada estratégia de busca.
2. **Tamanho dos trechos**: como o tamanho do chunk afeta a busca híbrida.
3. **Recusa**: o assistente responde perguntas do escopo e recusa as de fora?
4. **Resposta extrativa**: a resposta contém a evidência esperada?

Uso: python -m rag.evaluate
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
    return chunk.document == item["documento"] and _norm(item["evidencia"]) in _norm(chunk.text)


def retrieval_metrics(retriever, questions: list[dict], k: int = 5) -> dict[str, float]:
    hits1 = hits3 = hits5 = rr = 0.0
    for item in questions:
        results = retriever.search(item["pergunta"], k)
        rank = next((i for i, h in enumerate(results, 1) if is_relevant(h.chunk, item)), None)
        if rank:
            hits1 += rank <= 1
            hits3 += rank <= 3
            hits5 += rank <= 5
            rr += 1 / rank
    n = len(questions)
    return {"hit@1": hits1 / n, "hit@3": hits3 / n, "hit@5": hits5 / n, "mrr": rr / n}


def run(docs: Path = ROOT / "docs_exemplo", eval_dir: Path = ROOT / "eval") -> dict:
    questions = load_jsonl(eval_dir / "perguntas.jsonl")
    out_of_scope = load_jsonl(eval_dir / "fora_do_escopo.jsonl")
    sections = load_documents(find_documents(docs))
    chunks = chunk_sections(sections)

    missing = [q["pergunta"] for q in questions if not any(is_relevant(c, q) for c in chunks)]
    if missing:
        raise ValueError(f"Evidência não encontrada em nenhum trecho: {missing}")

    results: dict = {"n_perguntas": len(questions), "n_trechos": len(chunks), "busca": {}}
    for name, retriever in build_retrievers(chunks).items():
        results["busca"][name] = retrieval_metrics(retriever, questions)

    results["tamanho_trecho"] = {}
    for size in (40, 60, 90, 150, 250):
        c = chunk_sections(sections, max_words=size)
        results["tamanho_trecho"][size] = {
            "n_trechos": len(c),
            **retrieval_metrics(build_retrievers(c)["hibrido"], questions),
        }

    assistant = Assistant(chunks, generator=ExtractiveGenerator())
    answers = [assistant.ask(q["pergunta"]) for q in questions]
    refusals = [assistant.ask(q["pergunta"]) for q in out_of_scope]
    results["recusa"] = {
        "respondeu_no_escopo": sum(a.answered for a in answers) / len(answers),
        "recusou_fora_do_escopo": sum(not a.answered for a in refusals) / len(refusals),
    }
    results["resposta_extrativa_contem_evidencia"] = sum(
        _norm(q["evidencia"]) in _norm(a.text) for q, a in zip(questions, answers, strict=True)
    ) / len(questions)
    results["falhas_busca_hibrida"] = [
        q["pergunta"] for q in questions
        if not any(is_relevant(h.chunk, q) for h in assistant.retriever.search(q["pergunta"], 3))
    ]
    return results


def to_markdown(r: dict) -> str:
    pct = lambda v: f"{v:.0%}"  # noqa: E731
    lines = [
        "# Relatório de avaliação",
        "",
        f"{r['n_perguntas']} perguntas com resposta conhecida, {r['n_trechos']} trechos indexados.",
        "",
        "## Qualidade da busca",
        "",
        "| Estratégia | Hit@1 | Hit@3 | Hit@5 | MRR |",
        "|---|---|---|---|---|",
    ]
    for name, m in r["busca"].items():
        lines.append(f"| {name} | {pct(m['hit@1'])} | {pct(m['hit@3'])} | "
                     f"{pct(m['hit@5'])} | {m['mrr']:.3f} |")
    lines += ["", "## Tamanho do trecho (busca híbrida)", "",
              "| Palavras por trecho | Trechos | Hit@1 | Hit@3 | MRR |", "|---|---|---|---|---|"]
    for size, m in r["tamanho_trecho"].items():
        lines.append(f"| {size} | {m['n_trechos']} | {pct(m['hit@1'])} | "
                     f"{pct(m['hit@3'])} | {m['mrr']:.3f} |")
    rec = r["recusa"]
    lines += [
        "", "## Recusa e respostas", "",
        f"- Respondeu perguntas dentro do escopo: **{pct(rec['respondeu_no_escopo'])}**",
        f"- Recusou perguntas fora do escopo: **{pct(rec['recusou_fora_do_escopo'])}**",
        f"- Resposta extrativa contém a evidência esperada: "
        f"**{pct(r['resposta_extrativa_contem_evidencia'])}**",
        "", "## Perguntas em que a busca híbrida falhou (fora do top 3)", "",
    ]
    lines += [f"- {q}" for q in r["falhas_busca_hibrida"]] or ["- nenhuma"]
    return "\n".join(lines) + "\n"


def main() -> None:
    results = run()
    report = to_markdown(results)
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "avaliacao.md").write_text(report, encoding="utf-8")
    (ROOT / "reports" / "avaliacao.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
