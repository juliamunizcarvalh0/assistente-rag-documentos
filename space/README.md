---
title: Pergunte à Lei
emoji: ⚖️
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 8501
pinned: false
license: mit
short_description: RAG sobre CDC, LGPD e CLT com busca híbrida + Gemini
---

# ⚖️ Pergunte à Lei

Assistente que responde dúvidas do dia a dia sobre o **Código de Defesa do Consumidor**, a **LGPD** e a **CLT**, em português simples e **citando o artigo exato** da lei.

- **RAG** sobre 1.201 artigos oficiais do Planalto, só com a redação em vigor.
- **Busca híbrida:** BM25 implementado do zero + TF-IDF de caracteres, combinados por *Reciprocal Rank Fusion*.
- **Gemini** reescreve a pergunta em termos jurídicos antes da busca e explica a resposta citando os artigos.
- **Avaliação com conjunto de teste separado:** a reescrita pelo LLM eleva o acerto (artigo certo entre os 3 primeiros) de **42% para 67%** em perguntas novas.

Código, testes e avaliação completa: [github.com/juliamunizcarvalh0/assistente-rag-documentos](https://github.com/juliamunizcarvalh0/assistente-rag-documentos).

*Este Space é publicado automaticamente pelo GitHub Actions a cada atualização do repositório.*

> Conteúdo educativo, não substitui a orientação de um advogado. Não escreva dados pessoais nas perguntas.
