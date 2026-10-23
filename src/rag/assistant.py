"""Orquestra o fluxo RAG: indexar → buscar → decidir se dá para responder → gerar."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .generate import NOT_FOUND, ExtractiveGenerator, Generator, default_generator
from .ingest import Chunk, chunk_sections, find_documents, load_documents
from .retrievers import Hit, build_retrievers
from .text import tokenize


@dataclass
class Answer:
    question: str
    text: str
    hits: list[Hit]
    answered: bool


class Assistant:
    def __init__(
        self,
        chunks: list[Chunk],
        retriever: str = "hibrido",
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
        if isinstance(self.generator, ExtractiveGenerator) and not self.generator.idf:
            self.generator.idf = self.retrievers["bm25"].idf
        self.k = k
        self.min_coverage = min_coverage
        self.vocabulary = {t for c in chunks for t in tokenize(c.indexed_text)}

    @classmethod
    def from_folder(cls, folder: Path | str, **kwargs) -> Assistant:
        paths = find_documents(Path(folder))
        return cls(chunk_sections(load_documents(paths)), **kwargs)

    def coverage(self, question: str) -> float:
        """Fração dos termos da pergunta que existem em algum documento.
        Perguntas fora do escopo têm cobertura baixa e não são respondidas,
        o que evita alucinações e economiza chamadas ao LLM."""
        terms = set(tokenize(question))
        if not terms:
            return 0.0
        return len(terms & self.vocabulary) / len(terms)

    def ask(self, question: str) -> Answer:
        if self.coverage(question) < self.min_coverage:
            return Answer(question, NOT_FOUND, [], answered=False)
        hits = self.retriever.search(question, self.k)
        if not hits:
            return Answer(question, NOT_FOUND, [], answered=False)
        text = self.generator.answer(question, hits)
        return Answer(question, text, hits, answered=text != NOT_FOUND)
