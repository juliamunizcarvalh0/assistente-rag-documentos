"""Glossário: palavras do dia a dia → termos que a lei usa.

A busca por palavras (BM25) só encontra o artigo quando a pergunta usa as mesmas
palavras da lei. Mas as pessoas dizem "apagar meus dados", e a LGPD diz
"eliminação"; dizem "patrão", e a CLT diz "empregador". Este glossário expande a
pergunta com os termos jurídicos antes da busca. É o plano B sem custo: no app,
o Gemini faz uma reescrita mais completa.

As entradas foram escritas a partir do vocabulário geral das três leis, e não
para perguntas específicas. A avaliação mede o efeito num conjunto de perguntas
separado, que não foi usado para ajustar o glossário.
"""

from __future__ import annotations

import re

from .text import strip_accents

# Cada chave é uma expressão do dia a dia (sem acento, minúscula); o valor são os
# termos jurídicos acrescentados à busca.
GLOSSARY: dict[str, str] = {
    # --- consumidor --------------------------------------------------------
    "loja": "fornecedor",
    "vendedor": "fornecedor",
    "comprar": "consumidor fornecimento produto",
    "compra": "consumidor fornecimento produto",
    "devolver": "desistir arrependimento restituição",
    "devolucao": "desistir arrependimento restituição",
    "desistir": "arrependimento",
    "defeito": "vício",
    "estragado": "vício defeito",
    "quebrado": "vício defeito",
    "consertar": "vício sanado",
    "conserto": "vício sanado",
    "nome sujo": "cadastro banco de dados consumidor",
    "negativado": "cadastro banco de dados consumidor",
    "spc": "cadastro banco de dados consumidor",
    "serasa": "cadastro banco de dados consumidor",
    "propaganda": "publicidade",
    "anuncio": "publicidade oferta",
    "venda casada": "condicionar fornecimento outro produto",
    "junto com outro": "condicionar fornecimento outro produto",
    "processar": "ação reparação prescrição",
    # --- dados pessoais ----------------------------------------------------
    "meus dados": "dados pessoais titular tratamento",
    "apagar": "eliminação",
    "excluir": "eliminação",
    "deletar": "eliminação",
    "autorizar": "consentimento",
    "autorizacao": "consentimento",
    "permissao": "consentimento",
    "cancelar": "revogação revogado",
    "vazar": "incidente de segurança",
    "vazarem": "incidente de segurança",
    "vazamento": "incidente de segurança",
    "hacker": "incidente de segurança",
    "outro pais": "transferência internacional",
    "exterior": "transferência internacional",
    "dpo": "encarregado",
    "responsavel pela protecao": "encarregado",
    "criancas": "crianças adolescentes",
    "filho menor": "crianças adolescentes",
    "concorrente": "portabilidade outro fornecedor",
    "levar meus dados": "portabilidade",
    # --- trabalho ----------------------------------------------------------
    "patrao": "empregador",
    "chefe": "empregador",
    "funcionario": "empregado",
    "trabalhador": "empregado",
    "demissao": "despedida rescisão contrato de trabalho",
    "demitido": "despedida rescisão contrato de trabalho",
    "demitida": "despedida rescisão contrato de trabalho",
    "mandado embora": "despedida rescisão",
    "almoco": "repouso alimentação intervalo",
    "almocar": "repouso alimentação intervalo",
    "hora extra": "horas suplementares extraordinárias",
    "casar": "casamento",
    "faltar": "deixar de comparecer ao serviço faltas",
    "noite": "noturno",
    "dividir": "fracionamento períodos",
    "partes": "períodos",
    "rescisao": "rescisão quitação parcelas",
    "carteira assinada": "carteira de trabalho",
}

_KEYS = sorted(GLOSSARY, key=len, reverse=True)  # expressões longas primeiro


def expand_query(question: str) -> str:
    """Devolve a pergunta com os termos jurídicos correspondentes acrescentados."""
    normalized = " " + re.sub(r"[^a-z0-9 ]", " ", strip_accents(question.lower())) + " "
    extra = []
    for key in _KEYS:
        if f" {key} " in normalized:
            extra.append(GLOSSARY[key])
            normalized = normalized.replace(f" {key} ", " ")  # não casa de novo dentro
    return f"{question} {' '.join(extra)}" if extra else question
