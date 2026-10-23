"""Integração com LLMs testada sem rede, com clientes falsos."""

import types

import pytest

from rag.assistant import Assistant
from rag.generate import (
    NOT_FOUND,
    SYSTEM_PROMPT,
    GeminiGenerator,
    QuotaExceededError,
)
from rag.ingest import Chunk
from rag.retrievers import BM25Retriever

CHUNKS = [
    Chunk(0, "CDC", "Art. 49. O consumidor pode desistir do contrato, no prazo de 7 dias "
                    "a contar de sua assinatura ou do ato de recebimento do produto, sempre que "
                    "a contratação ocorrer fora do estabelecimento comercial.",
          heading="Da Proteção Contratual", label="CDC, art. 49"),
    Chunk(1, "CLT", "Art. 129. Todo empregado terá direito anualmente ao gozo de um período de "
                    "férias, sem prejuízo da remuneração.", label="CLT, art. 129"),
    Chunk(2, "CDC", "Art. 26. O direito de reclamar pelos vícios aparentes caduca em trinta dias "
                    "para produtos não duráveis.", label="CDC, art. 26"),
]


class FakeGemini(GeminiGenerator):
    """GeminiGenerator com o cliente trocado por um falso."""

    def __init__(self, behaviour):
        self.models = list(self.DEFAULT_MODELS)
        self.calls = []

        def generate_content(model, contents, config):
            self.calls.append((model, contents, config))
            return types.SimpleNamespace(text=behaviour(model, contents, config))

        self.client = types.SimpleNamespace(
            models=types.SimpleNamespace(generate_content=generate_content))


def _client_error(code):
    from google.genai import errors

    return errors.ClientError(code, {"error": {"code": code, "message": "x", "status": "X"}})


def test_gemini_sends_articles_and_rules():
    gen = FakeGemini(lambda m, c, cfg: " Sim, em até 7 dias [1]. ")
    out = gen.answer("posso devolver?", BM25Retriever(CHUNKS).search("desistir contrato"))
    _, contents, config = gen.calls[0]
    assert out == "Sim, em até 7 dias [1]."
    assert config.system_instruction == SYSTEM_PROMPT
    assert "[1] (fonte: CDC, art. 49 — Da Proteção Contratual)" in contents


def test_gemini_tries_next_model_when_one_does_not_exist():
    def behaviour(model, contents, config):
        if model == GeminiGenerator.DEFAULT_MODELS[0]:
            raise _client_error(404)
        return "ok"

    gen = FakeGemini(behaviour)
    assert gen.answer("x", []) == "ok"
    assert gen.models[0] == GeminiGenerator.DEFAULT_MODELS[1]  # lembra o modelo que funcionou


def test_gemini_quota_error_is_explicit():
    def behaviour(model, contents, config):
        raise _client_error(429)

    with pytest.raises(QuotaExceededError):
        FakeGemini(behaviour).answer("x", [])


def test_rewrite_brings_legal_vocabulary_into_the_search():
    # "devolver compra da internet" não tem nenhuma palavra em comum com o art. 49.
    question = "Posso devolver uma compra da internet?"
    assert BM25Retriever(CHUNKS).search(question) == [] or \
        BM25Retriever(CHUNKS).search(question)[0].chunk.id != 0

    def behaviour(model, contents, config):
        if "palavras-chave" in contents:
            return "direito de arrependimento, desistir do contrato, fora do estabelecimento"
        return "Sim, em até 7 dias [1]."

    answer = Assistant(CHUNKS, generator=FakeGemini(behaviour)).ask(question)
    assert answer.hits[0].chunk.label == "CDC, art. 49"
    assert answer.search_query.startswith("direito de arrependimento")
    assert answer.mode == "gemini" and answer.answered


def test_falls_back_to_extractive_when_quota_runs_out():
    def behaviour(model, contents, config):
        raise _client_error(429)

    answer = Assistant(CHUNKS, generator=FakeGemini(behaviour)).ask(
        "Quantos dias de férias o empregado tem direito?")
    assert answer.mode == "extrativo"
    assert "cota" in answer.notes
    assert "férias" in answer.text


def test_law_filter_only_returns_chosen_laws():
    assistant = Assistant(CHUNKS, generator=FakeGemini(lambda m, c, cfg: "resposta [1]"))
    answer = assistant.ask("prazo de dias", documents=["CLT"])
    assert {h.chunk.document for h in answer.hits} == {"CLT"}


def test_llm_saying_not_found_is_not_an_answer():
    answer = Assistant(CHUNKS, generator=FakeGemini(lambda m, c, cfg: NOT_FOUND)).ask(
        "prazo para desistir do contrato")
    assert not answer.answered and answer.hits == []

