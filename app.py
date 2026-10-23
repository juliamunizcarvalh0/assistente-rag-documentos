"""Pergunte à Lei: chat sobre CDC, LGPD e CLT. Rodar: streamlit run app.py"""

from __future__ import annotations

import html
import os
import re
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from rag.assistant import Assistant  # noqa: E402
from rag.generate import GeminiGenerator  # noqa: E402
from rag.ingest import chunk_sections, find_documents, load_documents  # noqa: E402

LAWS = {
    "CDC": ("🛒", "Consumidor"),
    "LGPD": ("🔒", "Dados pessoais"),
    "CLT": ("💼", "Trabalho"),
}
EXAMPLES = {
    "CDC": ["Posso devolver uma compra feita pela internet?",
            "Quanto tempo tenho para reclamar de um defeito?"],
    "LGPD": ["Uma empresa pode usar meus dados sem eu autorizar?",
             "Posso pedir para apagarem meus dados?"],
    "CLT": ["Quantos dias de férias eu tenho por ano?",
            "Quanto tempo de intervalo tenho para almoço?"],
}

st.set_page_config(page_title="Pergunte à Lei", page_icon="⚖️", layout="centered")
st.markdown("""
<style>
  .hero h1 {font-size: 2.4rem; margin-bottom: .2rem}
  .hero p {color: #6b7280; font-size: 1.05rem; margin-top: 0}
  .src-card {border: 1px solid rgba(128,128,128,.25); border-radius: 12px;
             padding: .7rem .9rem; margin: .4rem 0}
  .src-card .tag {display: inline-block; font-weight: 600; font-size: .8rem;
                  padding: .1rem .55rem; border-radius: 999px;
                  background: rgba(37,99,235,.12); color: #2563eb; margin-right: .4rem}
  .src-card .where {color: #6b7280; font-size: .85rem}
  .cite {font-size: .72rem; font-weight: 700; color: #2563eb; vertical-align: super}
  .mode {color: #6b7280; font-size: .8rem}
</style>
""", unsafe_allow_html=True)


def secret(name: str) -> str | None:
    try:
        return st.secrets.get(name) or os.getenv(name)
    except Exception:  # sem arquivo de secrets (rodando localmente)
        return os.getenv(name)


@st.cache_resource(show_spinner="Carregando as leis…")
def get_assistant(api_key: str | None) -> Assistant:
    chunks = chunk_sections(load_documents(find_documents(ROOT / "leis")))
    generator = GeminiGenerator(api_key=api_key) if api_key else None
    return Assistant(chunks, generator=generator)


def render_answer(text: str) -> str:
    """Transforma [1] em uma pequena citação sobrescrita."""
    return re.sub(r"\[(\d+)\]", r'<span class="cite">[\1]</span>', html.escape(text))


def render_sources(sources: list[dict]) -> None:
    for i, src in enumerate(sources, start=1):
        st.markdown(
            f'<div class="src-card"><span class="tag">[{i}] {html.escape(src["label"])}</span>'
            f'<span class="where">{html.escape(src["heading"] or "")}</span></div>',
            unsafe_allow_html=True,
        )
        with st.expander("Ler o artigo completo"):
            st.write(src["text"])


try:
    assistant = get_assistant(secret("GEMINI_API_KEY"))
except ValueError:
    st.error("Nenhuma lei encontrada na pasta `leis/`. Veja o README para adicionar os textos.")
    st.stop()

with st.sidebar:
    st.subheader("Sobre o projeto")
    st.write(
        "Assistente com **RAG** (Retrieval-Augmented Generation): busca os artigos mais "
        "relevantes com **busca híbrida** (BM25 + TF-IDF) e uma IA explica a resposta "
        "citando a fonte."
    )
    st.metric("Artigos indexados", f"{len(assistant.chunks):,}".replace(",", "."))
    st.caption("Textos oficiais do Planalto, só com a redação em vigor.")
    st.link_button("Ver o código no GitHub",
                   "https://github.com/juliamunizcarvalh0/assistente-rag-documentos")

st.markdown('<div class="hero"><h1>⚖️ Pergunte à Lei</h1>'
            "<p>Tire dúvidas sobre direitos do consumidor, dados pessoais e trabalho, "
            "com o artigo exato da lei.</p></div>", unsafe_allow_html=True)

available = [law for law in LAWS if law in assistant.documents]
selected = st.pills(
    "Buscar em", available, selection_mode="multi", default=available,
    format_func=lambda law: f"{LAWS[law][0]} {law} · {LAWS[law][1]}",
) or available

if "history" not in st.session_state:
    st.session_state.history = []

if not st.session_state.history:
    st.caption("Experimente perguntar:")
    examples = [q for law in selected for q in EXAMPLES.get(law, [])]
    choice = st.pills("Exemplos", examples, label_visibility="collapsed", key="example")
    if choice:
        st.session_state.pending = choice

for item in st.session_state.history:
    with st.chat_message(item["role"], avatar="🧑" if item["role"] == "user" else "⚖️"):
        if item["role"] == "user":
            st.write(item["text"])
            continue
        st.markdown(render_answer(item["text"]), unsafe_allow_html=True)
        if item["sources"]:
            render_sources(item["sources"])
        st.markdown(f'<span class="mode">{item["mode"]}</span>', unsafe_allow_html=True)

question = st.chat_input("Escreva sua dúvida, ex.: posso desistir de uma compra?")
question = question or st.session_state.pop("pending", None)
if question:
    st.session_state.history.append({"role": "user", "text": question})
    with st.spinner("Procurando nos artigos…"):
        try:
            answer = assistant.ask(question, documents=selected)
            mode = ("Resposta escrita pelo Gemini com base nos artigos citados."
                    if answer.mode == "gemini" else
                    "Modo sem IA: trechos copiados dos artigos mais relevantes.")
            if "cota" in answer.notes:
                mode = ("O limite gratuito da IA foi atingido. Mostrando os trechos da lei; "
                        "tente de novo em um minuto.")
            st.session_state.history.append({
                "role": "assistant", "text": answer.text, "mode": mode,
                "sources": [{"label": h.chunk.source, "heading": h.chunk.heading,
                             "text": h.chunk.text} for h in answer.hits],
            })
        except Exception as exc:
            st.session_state.history.append({
                "role": "assistant", "sources": [], "mode": "",
                "text": f"Desculpe, algo deu errado ao gerar a resposta ({type(exc).__name__}).",
            })
    st.rerun()

st.divider()
st.caption("⚠️ Conteúdo educativo, não substitui a orientação de um advogado. "
           "Não escreva dados pessoais nas perguntas: elas são enviadas a uma IA externa.")
