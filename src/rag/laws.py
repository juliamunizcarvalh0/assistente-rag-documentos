"""Leitura das leis no HTML oficial do Planalto, artigo por artigo.

As páginas "compiladas" do Planalto mostram o texto revogado riscado
(<strike>, <s> ou <del>). Esse texto é removido para que o assistente só
responda com base na redação em vigor. Também são retiradas as notas de
alteração, como "(Redação dada pela Lei nº ...)", e os artigos vetados ou
revogados.
"""

from __future__ import annotations

import re
from pathlib import Path

from bs4 import BeautifulSoup

from .ingest import Section
from .text import strip_accents

# Identificação das leis pelo número que aparece no título da página.
KNOWN_LAWS = {
    "8.078": ("CDC", "Código de Defesa do Consumidor (Lei 8.078/1990)"),
    "13.709": ("LGPD", "Lei Geral de Proteção de Dados (Lei 13.709/2018)"),
    "5.452": ("CLT", "Consolidação das Leis do Trabalho (Decreto-Lei 5.452/1943)"),
}

LEVELS = ["LIVRO", "TÍTULO", "CAPÍTULO", "SEÇÃO", "SUBSEÇÃO"]
_LEVEL_KEYS = ["LIVRO", "TITULO", "CAPITULO", "SECAO", "SUBSECAO"]
_LEVEL_RE = re.compile(r"^(LIVRO|T[ÍI]TULO|CAP[ÍI]TULO|SE[ÇC][ÃA]O|SUBSE[ÇC][ÃA]O)\b(.*)$",
                       re.IGNORECASE)
# "Art. 49.", "Art. 1º", "Art. 1o" (páginas antigas), "Art. 4º-A", "Art. 1º - Texto".
_ARTICLE_RE = re.compile(
    r"^Art\.?\s*(\d+(?:\.\d+)?)\s*[º°o]?(?:-([A-Z]{1,2})\b)?\s*[º°o]?\s*\.?\s*-?\s*"
)
_NOTE_RE = re.compile(
    r"\((?:\s*(?:Reda[çc][ãa]o dada|Inclu[íi]d[oa]|Acrescentad[oa]|Revogad[oa]|Vide|"
    r"Vig[êe]ncia|Renumerad[oa]|Express[ãa]o|Promulga[çc][ãa]o|Produ[çc][ãa]o de efeito|"
    r"Regulamento|Texto|Mensagem)[^()]*(?:\([^()]*\)[^()]*)*)\)",
    re.IGNORECASE,
)
_EMPTY_ARTICLE_RE = re.compile(r"^\W*(vetad[oa]|revogad[oa])\W*$", re.IGNORECASE)


def _read_html(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


def _clean(text: str) -> str:
    text = _NOTE_RE.sub("", text)
    return re.sub(r"\s+", " ", text).strip()


def identify_law(text: str, filename: str) -> tuple[str, str]:
    """Procura o número da lei no início da página ou no nome do arquivo."""
    head, name = text[:3000], filename.replace(".", "")
    for number, names in KNOWN_LAWS.items():
        if number in head or number.replace(".", "") in name:
            return names
    return filename, filename


def html_lines(html: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    # Riscado = revogado. Tabelas são cabeçalhos e quadros anexos, nunca artigos.
    for tag in soup(["strike", "s", "del", "script", "style", "table"]):
        tag.decompose()
    # Algumas páginas riscam o texto revogado por CSS em vez da tag <strike>.
    for tag in soup.find_all(style=re.compile(r"line-through", re.IGNORECASE)):
        tag.decompose()
    blocks = soup.find_all("p") or [soup.body or soup]
    lines = []
    for block in blocks:
        text = _clean(block.get_text(" "))
        if text:
            lines.append(text)
    return lines


def parse_law(path: Path) -> list[Section]:
    """Uma ``Section`` por artigo, com o capítulo/seção como título."""
    lines = html_lines(_read_html(path))
    short, full = identify_law(" ".join(lines[:30]), path.stem)

    hierarchy: dict[str, str] = {}
    pending_level: str | None = None
    sections: list[Section] = []
    article: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        body = " ".join(buffer[1:]).strip() if buffer else ""
        if article and buffer and not _EMPTY_ARTICLE_RE.match(body or buffer[0]):
            heading = " › ".join(v for k, v in hierarchy.items() if v and k != "LIVRO") or None
            sections.append(Section(
                document=short, text="\n".join(buffer), heading=heading,
                label=f"{short}, art. {article}", meta={"lei": full, "artigo": article},
            ))

    for line in lines:
        level = _LEVEL_RE.match(line)
        if level and len(line) < 120:
            key = LEVELS[_LEVEL_KEYS.index(strip_accents(level.group(1)).upper())]
            # Um nível novo apaga os níveis abaixo dele (novo capítulo zera a seção).
            for lower in LEVELS[LEVELS.index(key):]:
                hierarchy.pop(lower, None)
            # "CAPÍTULO VI Da Proteção Contratual" pode vir numa linha só ou em duas.
            parts = level.group(2).strip(" -–—").split(None, 1)
            hierarchy[key] = parts[1].strip(" -–—") if len(parts) > 1 else ""
            pending_level = None if len(parts) > 1 else key
            continue
        if pending_level and not _ARTICLE_RE.match(line) and len(line) < 150:
            hierarchy[pending_level] = line
            pending_level = None
            continue
        pending_level = None

        match = _ARTICLE_RE.match(line)
        if match:
            flush()
            article = match.group(1) + (f"-{match.group(2)}" if match.group(2) else "")
            if article == "1" and sections:
                # Um novo "Art. 1" depois de artigos já lidos é o início do texto anexo.
                # Na CLT, o decreto tem 2 artigos próprios, é assinado, e só então vem a
                # Consolidação em si, recomeçando do art. 1. Fica só o texto anexo.
                sections.clear()
            rest = line[match.end():].strip()
            buffer = [f"Art. {article}."] + ([rest] if rest else [])
            continue
        if article is None:
            continue  # preâmbulo, assinaturas ou anexos fora de um artigo
        if re.match(r"^(Bras[íi]lia|Rio de Janeiro),", line) or \
                re.match(r"^(QUADRO|ANEXO)\b", line):
            # Assinatura ou tabela anexa: encerra o artigo atual sem incluir a linha.
            flush()
            article, buffer = None, []
            continue
        buffer.append(line)
    flush()
    return sections


def is_law_file(path: Path) -> bool:
    return path.suffix.lower() in {".htm", ".html"}
