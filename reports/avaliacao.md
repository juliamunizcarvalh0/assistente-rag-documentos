# Relatório de avaliação da busca

Índice: 1323 trechos (CDC: 133, CLT: 1091, LGPD: 99). Perguntas escritas em linguagem do dia a dia, cada uma com o artigo e o trecho exato que a responde.

- **Desenvolvimento** (36 perguntas): usado para analisar os erros e melhorar a busca.
- **Teste** (24 perguntas, outros assuntos): escrito à parte e **não** usado para ajustar nada. Mostra se as melhorias generalizam.

Resultados **sem IA**. No app, o Gemini ainda reescreve a pergunta antes da busca.

## Hit@3 e MRR por estratégia

| Estratégia | Hit@3 (desenv.) | MRR (desenv.) | Hit@3 (teste) | MRR (teste) |
|---|---|---|---|---|
| bm25 | 44% | 0.319 | 33% | 0.271 |
| tfidf_char | 39% | 0.284 | 29% | 0.240 |
| hibrido | 50% | 0.329 | 38% | 0.306 |
| hibrido_glossario | 81% | 0.529 | 42% | 0.312 |

## Por lei (hibrido_glossario, conjunto de teste)

| Lei | Perguntas | Hit@1 | Hit@3 | MRR |
|---|---|---|---|---|
| CDC | 8 | 50% | 50% | 0.500 |
| CLT | 8 | 12% | 25% | 0.188 |
| LGPD | 8 | 12% | 50% | 0.250 |

Perguntas fora do escopo recusadas (modo sem IA): **33%**

## Erros no conjunto de desenvolvimento (artigo certo fora do top 3)

- Em quanto tempo a loja precisa resolver o defeito do produto? — esperado **CDC, art. 18**, veio CDC, art. 23, CDC, art. 24, CDC, art. 26
- Uma empresa pode usar meus dados sem eu autorizar? — esperado **LGPD, art. 7**, veio LGPD, art. 8, LGPD, art. 9, LGPD, art. 7
- Qual é a multa para quem descumpre a LGPD? — esperado **LGPD, art. 52**, veio LGPD, art. 54, LGPD, art. 18, LGPD, art. 55-J
- A LGPD vale para quem usa dados só para fins pessoais? — esperado **LGPD, art. 4**, veio LGPD, art. 6, LGPD, art. 33, LGPD, art. 58-A
- Os dados precisam ser apagados quando a empresa não usa mais? — esperado **LGPD, art. 16**, veio CLT, art. 359, LGPD, art. 43, CLT, art. 485
- Quanto a mais eu ganho por hora extra? — esperado **CLT, art. 59**, veio CLT, art. 58-A, CLT, art. 58-A, CLT, art. 250
- O que pode dar demissão por justa causa? — esperado **CLT, art. 482**, veio CLT, art. 479, CLT, art. 502, CLT, art. 497

## Erros no conjunto de teste (artigo certo fora do top 3)

- Comprei um produto com defeito, posso pedir meu dinheiro de volta? — esperado **CDC, art. 18**, veio CDC, art. 23, CDC, art. 26, CDC, art. 17
- A loja é obrigada a cumprir o preço que anunciou? — esperado **CDC, art. 30**, veio CDC, art. 107, CDC, art. 51, CDC, art. 54-F
- Recebi um produto que não pedi, tenho que pagar? — esperado **CDC, art. 39**, veio CDC, art. 49, CDC, art. 13, CDC, art. 18
- O serviço foi mal feito, o que posso exigir? — esperado **CDC, art. 20**, veio CDC, art. 35, CLT, art. 162, CLT, art. 343
- Meus dados estão errados, posso pedir para corrigir? — esperado **LGPD, art. 18**, veio LGPD, art. 43, LGPD, art. 9, LGPD, art. 6
- O governo pode usar os meus dados? — esperado **LGPD, art. 23**, veio LGPD, art. 43, LGPD, art. 9, LGPD, art. 9
- Quem fiscaliza o cumprimento da LGPD? — esperado **LGPD, art. 55-J**, veio CLT, art. 626, CLT, art. 627-A, CLT, art. 627
- Se vazarem meus dados e eu tiver prejuízo, a empresa paga? — esperado **LGPD, art. 42**, veio LGPD, art. 44, LGPD, art. 48, LGPD, art. 21
- Até que dia o salário tem que cair na conta? — esperado **CLT, art. 459**, veio CLT, art. 83, CLT, art. 78, CLT, art. 465
- Posso vender uma parte das minhas férias? — esperado **CLT, art. 143**, veio CLT, art. 136, CLT, art. 129, CLT, art. 128
- O que a lei considera trabalho em home office? — esperado **CLT, art. 75-B**, veio CLT, art. 463, CLT, art. 492, CLT, art. 878-A
- Uma funcionária grávida pode ser demitida? — esperado **CLT, art. 391-A**, veio CLT, art. 497, CLT, art. 479, CLT, art. 494
- Quanto tempo de folga semanal eu tenho? — esperado **CLT, art. 67**, veio CLT, art. 229, CLT, art. 58-A, CLT, art. 58-A
- Posso ser obrigado a trabalhar em feriado? — esperado **CLT, art. 70**, veio CLT, art. 138, CLT, art. 136, CLT, art. 134
