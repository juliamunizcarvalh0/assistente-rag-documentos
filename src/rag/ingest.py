"""Leitura de documentos (PDF, Markdown, TXT) e divisão em trechos (chunks)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from pypdf import PdfReader

from .text import split_sentences

SUPPORTED = {".pdf", ".md", ".txt"}


@dataclass
class Section:
    document: str
    text: str
    page: int | None = None
    heading: str | None = None


@dataclass
class Chunk:
    id: int
    document: str
    text: str
    page: int | None = None
    heading: str | None = None
    meta: dict = field(default_factory=dict)

    @property
    def indexed_text(self) -> str:
        """O título da seção entra no texto indexado: ajuda muito a busca."""
        return f"{self.heading}. {self.text}" if self.heading else self.text

    @property
    def source(self) -> str:
        parts = [f"p. {self.page}" if self.page else None, self.heading]
        where = ", ".join(p for p in parts if p)
        return f"{self.document}" + (f" ({where})" if where else "")


def _looks_like_heading(line: str) -> bool:
    """Linha curta, sem pontuação final e começando com maiúscula: provável título."""
    line = line.strip()
    return (
        0 < len(line) <= 45
        and len(line.split()) <= 6
        and line[0].isupper()
        and line[-1] not in ".,;:!?)"
    )


def read_pdf(path: Path) -> list[Section]:
    """Lê cada página e separa as seções pelos títulos detectados, que o PDF
    não marca como o Markdown faz."""
    reader = PdfReader(str(path))
    sections: list[Section] = []
    heading = None
    for page_number, page in enumerate(reader.pages, start=1):
        buffer: list[str] = []
        for line in (page.extract_text() or "").splitlines():
            if _looks_like_heading(line):
                if "".join(buffer).strip():
                    sections.append(Section(path.name, "\n".join(buffer), page_number, heading))
                heading, buffer = line.strip(), []
            else:
                buffer.append(line)
        if "".join(buffer).strip():
            sections.append(Section(path.name, "\n".join(buffer), page_number, heading))
    return sections


def read_markdown(path: Path, text: str | None = None) -> list[Section]:
    """Divide o texto pelos títulos (#, ##, ...) para manter o contexto de cada seção."""
    text = text if text is not None else path.read_text(encoding="utf-8")
    sections: list[Section] = []
    heading, buffer = None, []
    for line in text.splitlines():
        match = re.match(r"^#{1,6}\s+(.*)", line)
        if match:
            if "".join(buffer).strip():
                sections.append(Section(path.name, "\n".join(buffer), heading=heading))
            heading, buffer = match.group(1).strip(), []
        else:
            buffer.append(line)
    if "".join(buffer).strip():
        sections.append(Section(path.name, "\n".join(buffer), heading=heading))
    return sections


def load_documents(paths: list[Path]) -> list[Section]:
    sections: list[Section] = []
    for path in paths:
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            sections += read_pdf(path)
        elif suffix in {".md", ".txt"}:
            sections += read_markdown(path)
    return sections


def find_documents(folder: Path) -> list[Path]:
    return sorted(p for p in folder.rglob("*") if p.suffix.lower() in SUPPORTED)


def chunk_sections(
    sections: list[Section], max_words: int = 90, overlap_sentences: int = 1
) -> list[Chunk]:
    """Agrupa frases inteiras até ``max_words`` palavras, com sobreposição entre
    trechos vizinhos para não cortar uma informação no meio."""
    chunks: list[Chunk] = []
    for section in sections:
        clean = re.sub(r"[*_`]", "", section.text)
        sentences = split_sentences(clean)
        current: list[str] = []
        for sentence in sentences:
            words = sum(len(s.split()) for s in current)
            if current and words + len(sentence.split()) > max_words:
                chunks.append(Chunk(len(chunks), section.document, " ".join(current),
                                    section.page, section.heading))
                current = current[-overlap_sentences:] if overlap_sentences else []
            current.append(sentence)
        if current:
            text = " ".join(current)
            last = chunks[-1] if chunks else None
            same_section = last and last.document == section.document and \
                last.page == section.page and last.heading == section.heading
            # Evita um trecho final que só repete a frase de sobreposição.
            if not (same_section and text in last.text):
                chunks.append(Chunk(len(chunks), section.document, text,
                                    section.page, section.heading))
    return chunks
