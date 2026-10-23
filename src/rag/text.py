"""Normalização e tokenização de texto em português."""

from __future__ import annotations

import re
import unicodedata

STOPWORDS = set("""
a à ao aos as às até com como da das de dela dele do dos e é ela ele eles em entre era
essa esse esta este eu foi há isso isto já la lhe mais mas me mesmo meu minha muito na
nas nem no nos nós o os ou para pela pelas pelo pelos por qual quando que quem se sem
ser seu seus sua suas também te tem têm um uma umas uns vai você vocês ter são está
estão posso pode podem preciso devo deve qual quais quanto quantos quanta quantas sobre
minhas meus num numa faço fazer eu
""".split())

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:[.,][0-9]+)*")
_SENTENCE_RE = re.compile(r"(?<=[.!?:;])\s+(?=[A-ZÁÉÍÓÚÂÊÔÃÕÇ0-9\"*(-])")


def strip_accents(text: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    )


def stem(token: str) -> str:
    """Stemmer leve: remove plurais e sufixos comuns, sem dependências externas."""
    if len(token) <= 3 or token[0].isdigit():
        return token
    # 1. plurais e sufixos nominais
    for suffix in ("amento", "imento", "mente", "acoes", "icoes", "acao", "icao",
                   "ores", "oes", "aes", "ais", "eis", "res", "s"):
        if token.endswith(suffix) and len(token) - len(suffix) >= 3:
            token = token[: -len(suffix)]
            break
    # 2. gerúndio e particípio: "trabalhando", "divididas" (já sem o plural)
    for suffix in ("ando", "endo", "indo", "ada", "ado", "ida", "ido"):
        if token.endswith(suffix) and len(token) - len(suffix) >= 4:
            token = token[: -len(suffix)]
            break
    # 3. infinitivo e "-or": "aceitar" -> "aceita", "fornecedor" -> "fornecedo"
    if token.endswith(("ar", "er", "ir", "or")) and len(token) > 4:
        token = token[:-1]
    # 4. vogal final: "suspeito"/"suspeita", "pendrive"/"pendrives" -> mesmo radical
    if token.endswith(("a", "e", "i", "o")) and len(token) > 4:
        token = token[:-1]
    return token


def tokenize(text: str, remove_stopwords: bool = True) -> list[str]:
    """Minúsculas, sem acentos, sem stopwords e com stemming leve."""
    text = re.sub(r"\be-mails?\b", "email", strip_accents(text.lower()))
    tokens = _TOKEN_RE.findall(text)
    if remove_stopwords:
        stop = {strip_accents(w) for w in STOPWORDS}
        tokens = [t for t in tokens if t not in stop]
    return [stem(t) for t in tokens]


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    return [s.strip() for s in _SENTENCE_RE.split(text) if s.strip()]
