"""Geração da resposta a partir dos trechos recuperados.

Dois modos:
- ``ClaudeGenerator``: usa um LLM (API da Anthropic) quando ``ANTHROPIC_API_KEY``
  está definida. O modelo pode ser trocado pela variável ``RAG_MODEL``.
- ``ExtractiveGenerator``: sem API e sem custo; seleciona as frases mais
  relevantes dos trechos. Garante que o projeto roda em qualquer máquina.
"""

from __future__ import annotations

import os
from typing import Protocol

from .retrievers import Hit
from .text import split_sentences, tokenize

NOT_FOUND = "Não encontrei essa informação nos documentos disponíveis."

SYSTEM_PROMPT = f"""Você é um assistente que responde perguntas usando APENAS os trechos de
documentos fornecidos. Regras:
1. Responda em português, de forma direta e curta.
2. Cite a fonte de cada afirmação com o número do trecho entre colchetes, ex.: [1] ou [2][3].
3. Se os trechos não contiverem a resposta, responda exatamente: "{NOT_FOUND}"
4. Nunca invente valores, prazos ou regras que não estejam nos trechos."""


def format_context(hits: list[Hit]) -> str:
    return "\n\n".join(
        f"[{i}] (fonte: {h.chunk.source})\n{h.chunk.text}" for i, h in enumerate(hits, start=1)
    )


class Generator(Protocol):
    name: str

    def answer(self, question: str, hits: list[Hit]) -> str: ...


class ClaudeGenerator:
    name = "claude"

    def __init__(self, model: str | None = None, max_tokens: int = 600):
        import anthropic

        self.client = anthropic.Anthropic()
        self.model = model or os.getenv("RAG_MODEL", "claude-haiku-5-5")
        self.max_tokens = max_tokens

    def answer(self, question: str, hits: list[Hit]) -> str:
        message = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": f"Trechos:\n\n{format_context(hits)}\n\nPergunta: {question}",
            }],
        )
        return "".join(block.text for block in message.content if block.type == "text").strip()


class ExtractiveGenerator:
    """Escolhe as frases dos trechos que mais compartilham termos com a pergunta."""

    name = "extrativo"

    def __init__(self, max_sentences: int = 2, idf: dict[str, float] | None = None):
        self.max_sentences = max_sentences
        # Pesos IDF: palavras raras ("pendrive") valem mais que comuns ("dias").
        self.idf = idf or {}

    def answer(self, question: str, hits: list[Hit]) -> str:
        q_terms = set(tokenize(question))
        candidates = []
        for rank, hit in enumerate(hits[:3], start=1):
            for pos, sentence in enumerate(split_sentences(hit.chunk.text)):
                shared = q_terms & set(tokenize(sentence))
                score = sum(self.idf.get(t, 1.0) for t in shared)
                if score:
                    # Pequeno bônus para os trechos mais bem ranqueados.
                    candidates.append((score * (1 - 0.05 * (rank - 1)), rank, pos, sentence))
        if not candidates:
            return NOT_FOUND
        candidates.sort(key=lambda c: c[0], reverse=True)
        top = candidates[0][0]
        best = [c for c in candidates[: self.max_sentences] if c[0] >= 0.6 * top]
        best.sort(key=lambda c: (c[1], c[2]))  # mantém a ordem original do texto
        return " ".join(f"{s} [{rank}]" for _, rank, _, s in best)


def default_generator() -> Generator:
    if os.getenv("ANTHROPIC_API_KEY"):
        return ClaudeGenerator()
    return ExtractiveGenerator()
