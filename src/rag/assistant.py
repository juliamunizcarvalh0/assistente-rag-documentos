"""Orquestra o fluxo RAG: entender a pergunta → buscar → decidir se dá para
responder → gerar a resposta citando os artigos."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from .generate import (
    NOT_FOUND,
    ExtractiveGenerator,
    Generator,
    QuotaExceededError,
    default_generator,
)
from .ingest import Chunk, chunk_sections, find_documents, load_documents
from .retrievers import Hit, build_retrievers
from .text import tokenize

log = logging.getLogger(__name__)


@dataclass
class Answer:
    question: str
    text: str
    hits: list[Hit]
    answered: bool
    mode: str = "extrativo"                     # quem escreveu a resposta
    search_query: str | None = None             # pergunta reescrita, se houve
    notes: list[str] = field(default_factory=list)


class Assistant:
    def __init__(
        self,
        chunks: list[Chunk],
        retriever: str = "hibrido_glossario",
        generator: Generator | None = None,
        k: int = 4,
        min_coverage: float = 0.5,
    ):
        if not chunks:
            raise ValueError("Nenhum trecho para indexar: adicione documentos.")
        self.chunks = chunks
        self.retrievers = build_retrievers(chunks)
        self.retriever = self.retrievers[retriever]
        self.generator = generator or default_generator()
        # Plano B quando a cota gratuita do LLM acaba.
        self.fallback = ExtractiveGenerator(idf=self.retrievers["bm25"].idf)
        if isinstance(self.generator, ExtractiveGenerator) and not self.generator.idf:
            self.generator.idf = self.retrievers["bm25"].idf
        self.k = k
        self.min_coverage = min_coverage
        self.vocabulary = {t for c in chunks for t in tokenize(c.indexed_text)}
        self.documents = sorted({c.document for c in chunks})

    @classmethod
    def from_folder(cls, folder: Path | str, **kwargs) -> Assistant:
        paths = find_documents(Path(folder))
        return cls(chunk_sections(load_documents(paths)), **kwargs)

    @property
    def uses_llm(self) -> bool:
        return not isinstance(self.generator, ExtractiveGenerator)

    def coverage(self, question: str) -> float:
        """Fração dos termos da pergunta que existem em algum documento.
        Perguntas fora do escopo têm cobertura baixa e não são respondidas."""
        terms = set(tokenize(question))
        if not terms:
            return 0.0
        return len(terms & self.vocabulary) / len(terms)

    def search(self, query: str, documents: list[str] | None = None) -> list[Hit]:
        depth = self.k if not documents else self.k * 15
        hits = self.retriever.search(query, depth)
        if documents:
            hits = [h for h in hits if h.chunk.document in documents]
        return hits[: self.k]

    def _rewrite(self, question: str, notes: list[str]) -> str | None:
        rewrite = getattr(self.generator, "rewrite", None)
        if not rewrite:
            return None
        try:
            return rewrite(question) or None
        except QuotaExceededError:
            notes.append("cota")
        except Exception as exc:  # a reescrita é opcional: falhar não impede a resposta
            log.warning("Falha ao reescrever a pergunta: %s", exc)
        return None

    def _fused_search(self, question: str, rewritten: str | None, documents) -> list[Hit]:
        """Busca com a pergunta original e com a versão reescrita pelo LLM, e junta
        os resultados por Reciprocal Rank Fusion."""
        original = self.search(question, documents)
        if not rewritten:
            return original
        expanded = self.search(f"{question} {rewritten}", documents)
        scores: dict[int, float] = {}
        by_id: dict[int, Hit] = {}
        for ranking in (original, expanded):
            for rank, hit in enumerate(ranking, start=1):
                scores[hit.chunk.id] = scores.get(hit.chunk.id, 0) + 1 / (60 + rank)
                by_id[hit.chunk.id] = hit
        best = sorted(scores, key=scores.get, reverse=True)[: self.k]
        return [by_id[i] for i in best]

    def ask(self, question: str, documents: list[str] | None = None) -> Answer:
        notes: list[str] = []
        rewritten = self._rewrite(question, notes)
        # Recusa antes de gastar uma chamada de geração quando a pergunta (já com o
        # vocabulário jurídico da reescrita) não tem quase nada em comum com as leis.
        # Sem LLM o critério é mais rígido, porque não há quem recuse depois.
        threshold = self.min_coverage if not self.uses_llm else 1e-9
        if self.coverage(f"{question} {rewritten or ''}") < threshold:
            return Answer(question, NOT_FOUND, [], answered=False, search_query=rewritten)

        hits = self._fused_search(question, rewritten, documents)
        if not hits:
            return Answer(question, NOT_FOUND, [], answered=False, search_query=rewritten)

        generator, mode = self.generator, self.generator.name
        if "cota" in notes:
            generator, mode = self.fallback, self.fallback.name
        try:
            text = generator.answer(question, hits)
        except QuotaExceededError:
            notes.append("cota")
            text, mode = self.fallback.answer(question, hits), self.fallback.name
        answered = bool(text) and NOT_FOUND not in text
        return Answer(question, text or NOT_FOUND, hits if answered else [], answered,
                      mode=mode, search_query=rewritten, notes=notes)
