# Relatório de avaliação

43 perguntas com resposta conhecida, 30 trechos indexados.

## Qualidade da busca

| Estratégia | Hit@1 | Hit@3 | Hit@5 | MRR |
|---|---|---|---|---|
| bm25 | 95% | 100% | 100% | 0.973 |
| tfidf_char | 95% | 98% | 98% | 0.965 |
| hibrido | 98% | 98% | 100% | 0.983 |

## Tamanho do trecho (busca híbrida)

| Palavras por trecho | Trechos | Hit@1 | Hit@3 | MRR |
|---|---|---|---|---|
| 40 | 75 | 93% | 98% | 0.954 |
| 60 | 45 | 88% | 100% | 0.938 |
| 90 | 30 | 98% | 98% | 0.983 |
| 150 | 28 | 95% | 100% | 0.973 |
| 250 | 28 | 95% | 100% | 0.973 |

## Recusa e respostas

- Respondeu perguntas dentro do escopo: **98%**
- Recusou perguntas fora do escopo: **88%**
- Resposta extrativa contém a evidência esperada: **93%**

## Perguntas em que a busca híbrida falhou (fora do top 3)

- Em quantos dias devolvo o notebook quando saio da empresa?
