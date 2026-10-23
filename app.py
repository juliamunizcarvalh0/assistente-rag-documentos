"""Interface de chat. Rodar: streamlit run app.py"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from rag.assistant import Assistant  # noqa: E402
from rag.generate import ClaudeGenerator, ExtractiveGenerator  # noqa: E402
from rag.ingest import chunk_sections, find_documents, load_documents  # noqa: E402

st.set_page_config(page_title="Assistente de Documentos", page_icon="📄")


@st.cache_resource(show_spinner="Indexando documentos…")
def build_chunks(files: tuple[tuple[str, bytes], ...]):
    if not files:
        return chunk_sections(load_documents(find_documents(ROOT / "docs_exemplo")))
    folder = Path(tempfile.mkdtemp())
    for name, data in files:
        (folder / Path(name).name).write_bytes(data)
    return chunk_sections(load_documents(find_documents(folder)))


with st.sidebar:
    st.header("Documentos")
    uploads = st.file_uploader("Envie PDFs, .md ou .txt", type=["pdf", "md", "txt"],
                               accept_multiple_files=True)
    if not uploads:
        st.caption("Usando os documentos de exemplo da empresa fictícia Aurora Pagamentos.")
    busca = st.selectbox("Estratégia de busca", ["hibrido", "bm25", "tfidf_char"])
    api_key = st.text_input("Chave da API Anthropic (opcional)", type="password",
                            help="Sem chave, a resposta é extrativa: frases copiadas dos trechos.")

chunks = build_chunks(tuple((f.name, f.getvalue()) for f in uploads or []))
key = api_key or os.getenv("ANTHROPIC_API_KEY")
if key:
    os.environ["ANTHROPIC_API_KEY"] = key
    generator = ClaudeGenerator()
else:
    generator = ExtractiveGenerator()
assistant = Assistant(chunks, retriever=busca, generator=generator)

st.title("📄 Assistente de Documentos")
st.caption(f"{len(chunks)} trechos indexados · busca **{busca}** · "
           f"resposta **{'LLM (Claude)' if key else 'extrativa'}**")

if "history" not in st.session_state:
    st.session_state.history = []

for role, content, sources in st.session_state.history:
    with st.chat_message(role):
        st.markdown(content)
        if sources:
            with st.expander("Fontes"):
                for i, (src, text) in enumerate(sources, start=1):
                    st.markdown(f"**[{i}] {src}**\n\n> {text}")

exemplos = ["Qual o limite do Pix à noite?", "Posso usar pendrive no notebook da empresa?",
            "Em quanto tempo devo enviar a nota fiscal de uma despesa?"]
if not st.session_state.history and not uploads:
    st.write("Experimente perguntar:")
    cols = st.columns(len(exemplos))
    for col, ex in zip(cols, exemplos, strict=True):
        if col.button(ex, width="stretch"):
            st.session_state.pending = ex
            st.rerun()

question = st.chat_input("Faça uma pergunta sobre os documentos")
question = question or st.session_state.pop("pending", None)
if question:
    st.session_state.history.append(("user", question, []))
    try:
        answer = assistant.ask(question)
        sources = [(h.chunk.source, h.chunk.text) for h in answer.hits]
        st.session_state.history.append(("assistant", answer.text, sources))
    except Exception as exc:  # erro da API, chave inválida etc.
        st.session_state.history.append(("assistant", f"⚠️ Erro ao gerar a resposta: {exc}", []))
    st.rerun()
