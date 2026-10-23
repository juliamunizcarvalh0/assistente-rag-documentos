from pathlib import Path

import pytest

from rag.assistant import Assistant
from rag.evaluate import run
from rag.generate import NOT_FOUND, ExtractiveGenerator, format_context
from rag.ingest import Chunk
from rag.retrievers import BM25Retriever, HybridRetriever, build_retrievers

LEIS = Path(__file__).resolve().parents[1] / "leis"

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


@pytest.fixture(scope="module")
def laws_assistant():
    return Assistant.from_folder(LEIS, generator=ExtractiveGenerator())


def test_assistant_answers_from_the_real_law(laws_assistant):
    answer = laws_assistant.ask("Quantos dias de férias o empregado tem direito?")
    assert answer.answered and "[1]" in answer.text
    assert answer.hits[0].chunk.document == "CLT"


def test_law_filter_with_real_laws(laws_assistant):
    answer = laws_assistant.ask("prazo para reclamar de defeito", documents=["CDC"])
    assert {h.chunk.document for h in answer.hits} == {"CDC"}


def test_context_is_numbered_with_sources():
    hits = BM25Retriever(TOY).search("gato")
    assert format_context(hits).startswith("[1] (fonte: a.md)")


def test_empty_corpus_is_rejected():
    with pytest.raises(ValueError):
        Assistant([], generator=FakeLLM())


def test_evaluation_quality_bar():
    """Teste de regressão: mudanças no código não podem piorar a busca sem IA."""
    r = run()
    dev, test = r["conjuntos"]["desenvolvimento"], r["conjuntos"]["teste"]
    assert dev["busca"]["hibrido_glossario"]["hit@3"] >= 0.75
    assert test["busca"]["hibrido_glossario"]["hit@3"] >= 0.40
    # A fusão híbrida nunca pode ficar abaixo da melhor estratégia isolada.
    for data in (dev, test):
        best_single = max(data["busca"]["bm25"]["mrr"], data["busca"]["tfidf_char"]["mrr"])
        assert data["busca"]["hibrido"]["mrr"] >= best_single
