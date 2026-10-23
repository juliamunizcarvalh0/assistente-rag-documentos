from pathlib import Path

import pytest

from rag.assistant import Assistant
from rag.evaluate import run
from rag.generate import NOT_FOUND, ExtractiveGenerator, format_context
from rag.ingest import Chunk
from rag.retrievers import BM25Retriever, HybridRetriever, build_retrievers

DOCS = Path(__file__).resolve().parents[1] / "docs_exemplo"

TOY = [
    Chunk(0, "a.md", "O gato dorme no sofá da sala."),
    Chunk(1, "a.md", "O cachorro late para o carteiro todas as manhãs."),
    Chunk(2, "b.md", "Reembolso de despesas em até 30 dias com nota fiscal."),
]


class FakeLLM:
    name = "fake"

    def __init__(self):
        self.calls = 0

    def answer(self, question, hits):
        self.calls += 1
        return "resposta [1]"


def test_bm25_ranks_the_matching_chunk_first():
    hits = BM25Retriever(TOY).search("onde o gato dorme?")
    assert hits[0].chunk.id == 0


def test_bm25_ignores_chunks_without_query_terms():
    assert BM25Retriever(TOY).search("astronomia planetas") == []


def test_char_tfidf_handles_word_variations():
    hits = build_retrievers(TOY)["tfidf_char"].search("reembolsar despesa")
    assert hits[0].chunk.id == 2


def test_hybrid_fuses_rankings():
    class Fixed:
        def __init__(self, order):
            self.order = order

        def search(self, query, k=5):
            from rag.retrievers import Hit
            return [Hit(TOY[i], 1.0) for i in self.order][:k]

    # O trecho 1 é o 2º nos dois rankings e vence quem é 1º em só um deles.
    fused = HybridRetriever([Fixed([0, 1]), Fixed([2, 1])]).search("x", k=3)
    assert fused[0].chunk.id == 1


def test_assistant_refuses_out_of_scope_without_calling_llm():
    llm = FakeLLM()
    assistant = Assistant(TOY, generator=llm)
    answer = assistant.ask("Qual a capital da Austrália?")
    assert answer.text == NOT_FOUND and not answer.answered
    assert llm.calls == 0


def test_assistant_answers_with_sources():
    assistant = Assistant.from_folder(DOCS, generator=ExtractiveGenerator())
    answer = assistant.ask("Qual o limite do Pix à noite?")
    assert answer.answered
    assert "R$ 1.000" in answer.text and "[1]" in answer.text
    assert answer.hits[0].chunk.document == "guia_conta_digital.pdf"


def test_context_is_numbered_with_sources():
    hits = BM25Retriever(TOY).search("gato")
    assert format_context(hits).startswith("[1] (fonte: a.md)")


def test_empty_corpus_is_rejected():
    with pytest.raises(ValueError):
        Assistant([], generator=FakeLLM())


def test_evaluation_quality_bar():
    """Teste de regressão: mudanças no código não podem piorar a busca."""
    r = run()
    assert r["busca"]["hibrido"]["hit@3"] >= 0.90
    assert r["busca"]["hibrido"]["mrr"] >= 0.90
    assert r["recusa"]["recusou_fora_do_escopo"] >= 0.75
    assert r["recusa"]["respondeu_no_escopo"] >= 0.90


def test_claude_generator_sends_context_and_rules(monkeypatch):
    """Testa a integração com a API sem rede, usando um cliente falso."""
    import types

    import anthropic

    from rag.generate import SYSTEM_PROMPT, ClaudeGenerator

    captured = {}

    class FakeMessages:
        def create(self, **kwargs):
            captured.update(kwargs)
            block = types.SimpleNamespace(type="text", text=" O gato dorme no sofá [1]. ")
            return types.SimpleNamespace(content=[block])

    class FakeClient:
        messages = FakeMessages()

    monkeypatch.setattr(anthropic, "Anthropic", lambda: FakeClient())
    gen = ClaudeGenerator(model="modelo-teste")
    out = gen.answer("onde o gato dorme?", BM25Retriever(TOY).search("gato"))
    assert out == "O gato dorme no sofá [1]."
    assert captured["model"] == "modelo-teste"
    assert captured["system"] == SYSTEM_PROMPT
    assert "[1] (fonte: a.md)" in captured["messages"][0]["content"]
