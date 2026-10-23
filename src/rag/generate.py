"""Geração da resposta a partir dos artigos recuperados.

Três modos, escolhidos pela chave disponível:
- ``GeminiGenerator``: Gemini do Google (``GEMINI_API_KEY``), que tem plano gratuito.
- ``ClaudeGenerator``: Claude da Anthropic (``ANTHROPIC_API_KEY``).
- ``ExtractiveGenerator``: sem API e sem custo. Seleciona as frases mais relevantes
  dos artigos e garante que o projeto roda em qualquer máquina.

Os geradores com LLM também reescrevem a pergunta em vocabulário jurídico antes
da busca ("devolver compra da internet" -> "direito de arrependimento, desistência,
fora do estabelecimento comercial"), o que resolve a maior fraqueza da busca
por palavras: a pessoa e a lei usarem palavras diferentes.
"""

from __future__ import annotations

import os
from typing import Protocol

from .retrievers import Hit
from .text import split_sentences, tokenize

NOT_FOUND = "Não encontrei essa informação nas leis disponíveis."

SYSTEM_PROMPT = f"""Você é um assistente que explica leis brasileiras para pessoas comuns,
usando APENAS os artigos fornecidos. Regras:
1. Responda em português simples, sem juridiquês, em até 5 frases. Comece pela resposta direta
   (ex.: "Sim, você pode..." ou "O prazo é de...").
2. Cite cada afirmação com o número do trecho entre colchetes, ex.: [1] ou [2][3], e mencione o
   artigo quando ajudar (ex.: "segundo o art. 49 do CDC [1]").
3. Se os artigos não respondem à pergunta, responda exatamente: "{NOT_FOUND}"
4. Nunca invente prazos, valores ou regras que não estejam nos artigos.
5. Não diga que é aconselhamento jurídico."""

REWRITE_PROMPT = """Reescreva a pergunta abaixo como uma busca por palavras-chave na lei
brasileira. Use os termos técnicos que a lei usaria (ex.: "demitido" -> "despedida, rescisão do
contrato de trabalho"; "devolver compra da internet" -> "direito de arrependimento, desistir do
contrato, fora do estabelecimento comercial"). Responda só com as palavras-chave, numa linha,
sem explicação.

Pergunta: {question}"""


class QuotaExceededError(RuntimeError):
    """O limite gratuito do provedor acabou (HTTP 429)."""


def format_context(hits: list[Hit]) -> str:
    blocks = []
    for i, h in enumerate(hits, start=1):
        where = f" — {h.chunk.heading}" if h.chunk.heading else ""
        blocks.append(f"[{i}] (fonte: {h.chunk.source}{where})\n{h.chunk.text}")
    return "\n\n".join(blocks)


def _user_message(question: str, hits: list[Hit]) -> str:
    return f"Artigos:\n\n{format_context(hits)}\n\nPergunta: {question}"


class Generator(Protocol):
    name: str

    def answer(self, question: str, hits: list[Hit]) -> str: ...


class GeminiGenerator:
    name = "gemini"
    # Os nomes dos modelos mudam com frequência: se um não existir mais, tenta o próximo.
    DEFAULT_MODELS = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-flash-lite-latest"]

    def __init__(self, api_key: str | None = None, model: str | None = None):
        from google import genai

        self.client = genai.Client(api_key=api_key or os.environ["GEMINI_API_KEY"])
        preferred = model or os.getenv("GEMINI_MODEL")
        self.models = ([preferred] if preferred else []) + self.DEFAULT_MODELS

    def _generate(self, prompt: str, system: str | None = None, max_tokens: int = 500) -> str:
        from google.genai import errors, types

        config = types.GenerateContentConfig(
            system_instruction=system, temperature=0.2, max_output_tokens=max_tokens
        )
        last_error: Exception | None = None
        for model in list(self.models):
            try:
                response = self.client.models.generate_content(
                    model=model, contents=prompt, config=config
                )
                self.models = [model] + [m for m in self.models if m != model]
                return (response.text or "").strip()
            except errors.ClientError as exc:
                if exc.code == 429:
                    raise QuotaExceededError(str(exc)) from exc
                if exc.code == 404:  # modelo não existe: tenta o próximo
                    last_error = exc
                    continue
                raise
        raise RuntimeError(f"Nenhum modelo Gemini disponível: {last_error}")

    def answer(self, question: str, hits: list[Hit]) -> str:
        return self._generate(_user_message(question, hits), SYSTEM_PROMPT)

    def rewrite(self, question: str) -> str:
        return self._generate(REWRITE_PROMPT.format(question=question), max_tokens=80)


class ClaudeGenerator:
    name = "claude"

    def __init__(self, model: str | None = None, max_tokens: int = 600):
        import anthropic

        self.client = anthropic.Anthropic()
        self.model = model or os.getenv("RAG_MODEL", "claude-haiku-5-5")
        self.max_tokens = max_tokens

    def _create(self, content: str, system: str | None = None, max_tokens: int | None = None):
        kwargs = {"system": system} if system else {}
        message = self.client.messages.create(
            model=self.model, max_tokens=max_tokens or self.max_tokens,
            messages=[{"role": "user", "content": content}], **kwargs,
        )
        return "".join(block.text for block in message.content if block.type == "text").strip()

    def answer(self, question: str, hits: list[Hit]) -> str:
        return self._create(_user_message(question, hits), SYSTEM_PROMPT)

    def rewrite(self, question: str) -> str:
        return self._create(REWRITE_PROMPT.format(question=question), max_tokens=80)


class ExtractiveGenerator:
    """Escolhe as frases dos trechos que mais compartilham termos com a pergunta."""

    name = "extrativo"

    def __init__(self, max_sentences: int = 2, idf: dict[str, float] | None = None):
        self.max_sentences = max_sentences
        # Pesos IDF: palavras raras ("arrependimento") valem mais que comuns ("prazo").
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
    if os.getenv("GEMINI_API_KEY"):
        return GeminiGenerator()
    if os.getenv("ANTHROPIC_API_KEY"):
        return ClaudeGenerator()
    return ExtractiveGenerator()
