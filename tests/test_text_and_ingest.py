from pathlib import Path

from rag.ingest import Section, chunk_sections, find_documents, load_documents, read_markdown
from rag.text import split_sentences, tokenize

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_tokenize_normalizes_accents_stopwords_and_plurals():
    assert tokenize("As Férias") == tokenize("férias") == ["feri"]
    assert tokenize("pendrive") == tokenize("Pendrives")
    assert tokenize("aceitar") == tokenize("aceitos")
    assert tokenize("e-mail") == tokenize("email")


def test_numbers_are_kept_intact():
    assert "4,90" in tokenize("custa R$ 4,90")
    assert "1.000" in tokenize("limite de R$ 1.000")


def test_split_sentences():
    text = "Primeira frase. Segunda frase com R$ 4,90 cada! Terceira?"
    assert split_sentences(text) == ["Primeira frase.", "Segunda frase com R$ 4,90 cada!",
                                     "Terceira?"]


def test_markdown_sections_keep_headings(tmp_path):
    md = "# Título\nIntro.\n## Férias\nTexto de férias.\n## Benefícios\nTexto."
    sections = read_markdown(tmp_path / "x.md", md)
    assert [s.heading for s in sections] == ["Título", "Férias", "Benefícios"]


def test_chunks_respect_size_and_overlap():
    text = " ".join(f"Frase número {i} com algumas palavras." for i in range(40))
    chunks = chunk_sections([Section("doc.md", text)], max_words=30, overlap_sentences=1)
    assert len(chunks) > 1
    assert all(len(c.text.split()) <= 30 for c in chunks)
    last_sentence = split_sentences(chunks[0].text)[-1]
    assert chunks[1].text.startswith(last_sentence)  # sobreposição


def test_loads_pdf_with_page_numbers():
    """PDFs continuam suportados: títulos detectados viram seções."""
    pdf = load_documents(find_documents(FIXTURES))
    assert {s.page for s in pdf} == {1, 2}
    assert "Limites do Pix" in {s.heading for s in pdf}
    assert not any("Limites do Pix" in s.text for s in pdf)
