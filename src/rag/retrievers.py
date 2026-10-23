"""Estratégias de busca: BM25 (lexical), TF-IDF de caracteres (semântica leve)
e híbrida (Reciprocal Rank Fusion das duas)."""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import Protocol

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from .glossary import expand_query
from .ingest import Chunk
from .text import strip_accents, tokenize


@dataclass
class Hit:
    chunk: Chunk
    score: float


class Retriever(Protocol):
    name: str

    def search(self, query: str, k: int = 5) -> list[Hit]: ...


class BM25Retriever:
    """Implementação do BM25 Okapi do zero, para deixar claro como funciona."""

    name = "bm25"

    def __init__(self, chunks: list[Chunk], k1: float = 1.5, b: float = 0.75):
        self.chunks, self.k1, self.b = chunks, k1, b
        self.docs = [tokenize(c.indexed_text) for c in chunks]
        self.tf = [Counter(d) for d in self.docs]
        self.lengths = np.array([len(d) for d in self.docs], dtype=float)
        self.avg_len = self.lengths.mean() if len(chunks) else 0.0
        df = Counter(term for doc in self.docs for term in set(doc))
        n = len(chunks)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def scores(self, query: str) -> np.ndarray:
        q_terms = tokenize(query)
        out = np.zeros(len(self.chunks))
        for i, tf in enumerate(self.tf):
            norm = self.k1 * (1 - self.b + self.b * self.lengths[i] / self.avg_len)
            for term in q_terms:
                f = tf.get(term)
                if f:
                    out[i] += self.idf[term] * f * (self.k1 + 1) / (f + norm)
        return out

    def search(self, query: str, k: int = 5) -> list[Hit]:
        s = self.scores(query)
        order = np.argsort(-s)[:k]
        return [Hit(self.chunks[i], float(s[i])) for i in order if s[i] > 0]


class CharTfidfRetriever:
    """TF-IDF com n-gramas de caracteres: tolera variações de palavras
    ("reembolsada", "reembolso") e erros de digitação, sem baixar modelos."""

    name = "tfidf_char"

    def __init__(self, chunks: list[Chunk]):
        self.chunks = chunks
        self.vectorizer = TfidfVectorizer(
            analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True,
            preprocessor=lambda t: strip_accents(t.lower()),
        )
        self.matrix = normalize(self.vectorizer.fit_transform([c.indexed_text for c in chunks]))

    def search(self, query: str, k: int = 5) -> list[Hit]:
        q = normalize(self.vectorizer.transform([query]))
        s = (self.matrix @ q.T).toarray().ravel()
        order = np.argsort(-s)[:k]
        return [Hit(self.chunks[i], float(s[i])) for i in order if s[i] > 0]


class HybridRetriever:
    """Combina rankings com Reciprocal Rank Fusion: score = Σ 1 / (k + posição)."""

    name = "hibrido"

    def __init__(self, retrievers: list[Retriever], rrf_k: int = 60, depth: int = 20):
        self.retrievers, self.rrf_k, self.depth = retrievers, rrf_k, depth

    def search(self, query: str, k: int = 5) -> list[Hit]:
        fused: dict[int, float] = {}
        by_id: dict[int, Chunk] = {}
        for retriever in self.retrievers:
            for rank, hit in enumerate(retriever.search(query, self.depth), start=1):
                fused[hit.chunk.id] = fused.get(hit.chunk.id, 0.0) + 1 / (self.rrf_k + rank)
                by_id[hit.chunk.id] = hit.chunk
        best = sorted(fused, key=fused.get, reverse=True)[:k]
        return [Hit(by_id[i], fused[i]) for i in best]


class GlossaryRetriever:
    """Expande a pergunta com o glossário (dia a dia → termos da lei) antes de buscar."""

    name = "hibrido_glossario"

    def __init__(self, base: Retriever):
        self.base = base

    def search(self, query: str, k: int = 5) -> list[Hit]:
        return self.base.search(expand_query(query), k)


def build_retrievers(chunks: list[Chunk]) -> dict[str, Retriever]:
    bm25 = BM25Retriever(chunks)
    tfidf = CharTfidfRetriever(chunks)
    hybrid = HybridRetriever([bm25, tfidf])
    return {"bm25": bm25, "tfidf_char": tfidf, "hibrido": hybrid,
            "hibrido_glossario": GlossaryRetriever(hybrid)}
