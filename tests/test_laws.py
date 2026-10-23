"""O leitor de leis é testado com uma página fictícia que imita o HTML do Planalto."""

from rag.ingest import chunk_sections, load_documents
from rag.laws import parse_law

PAGE = """<html><head><meta charset="windows-1252"></head><body>
<p align="center">LEI Nº 8.078, DE 11 DE SETEMBRO DE 1990.</p>
<p>Dispõe sobre a proteção do consumidor e dá outras providências.</p>
<p align="center">TÍTULO I</p>
<p align="center">Dos Direitos</p>
<p align="center">CAPÍTULO I</p>
<p align="center">Disposições Gerais</p>
<p>Art. 1º Esta lei de teste estabelece regras gerais.</p>
<p>Art. 2º <strike>O prazo é de dez dias.</strike></p>
<p>O prazo é de quinze dias. (Redação dada pela Lei nº 99.999, de 2020)</p>
<p>Parágrafo único. O prazo conta da entrega.
<span style="text-decoration: line-through">Prazo antigo de vinte dias.</span></p>
<p>Art. 3º (VETADO).</p>
<p align="center">CAPÍTULO II - Da Garantia</p>
<p align="center">Seção I</p>
<p align="center">Dos Prazos</p>
<p>Art. 4º-A O fornecedor responde pelos defeitos: (Incluído pela Lei nº 88.888, de 2015)</p>
<p>I - durante a garantia;</p>
<p>II - após a garantia, nos casos previstos.</p>
<p>Brasília, 11 de setembro de 1990; 169º da Independência.</p>
<p>QUADRO ANEXO</p><p>Tabela que não deve entrar.</p>
</body></html>"""


def _write(tmp_path):
    path = tmp_path / "lei.htm"
    path.write_bytes(PAGE.encode("cp1252"))  # o Planalto usa essa codificação
    return path


def test_parses_articles_and_identifies_the_law(tmp_path):
    sections = parse_law(_write(tmp_path))
    assert [s.label for s in sections] == ["CDC, art. 1", "CDC, art. 2", "CDC, art. 4-A"]
    assert all(s.document == "CDC" for s in sections)
    assert sections[0].meta["lei"].startswith("Código de Defesa do Consumidor")


def test_removes_revoked_text_and_amendment_notes(tmp_path):
    art2 = parse_law(_write(tmp_path))[1].text
    assert "dez dias" not in art2          # riscado = revogado
    assert "vinte dias" not in art2        # riscado via CSS
    assert "quinze dias" in art2
    assert "Redação dada" not in art2
    assert "Parágrafo único" in art2


def test_skips_vetoed_articles_and_signatures(tmp_path):
    labels = [s.label for s in parse_law(_write(tmp_path))]
    assert "CDC, art. 3" not in labels
    assert "CDC, art. 99" not in labels


def test_keeps_chapter_and_section_as_heading(tmp_path):
    sections = parse_law(_write(tmp_path))
    assert sections[0].heading == "Dos Direitos › Disposições Gerais"
    assert sections[2].heading == "Dos Direitos › Da Garantia › Dos Prazos"


def test_articles_become_whole_chunks(tmp_path):
    chunks = chunk_sections(load_documents([_write(tmp_path)]))
    art4 = chunks[-1]
    assert art4.source == "CDC, art. 4-A"
    assert "I - durante a garantia;" in art4.text and "II - após" in art4.text


def test_long_articles_are_split_but_keep_the_article_label(tmp_path):
    long_page = PAGE.replace(
        "<p>I - durante a garantia;</p>",
        "".join(f"<p>{n} - item número {n} com várias palavras de teste;</p>"
                for n in ["I", "II", "III", "IV", "V", "VI", "VII", "VIII"] * 10),
    )
    path = tmp_path / "longa.htm"
    path.write_bytes(long_page.encode("cp1252"))
    parts = [c for c in chunk_sections(load_documents([path])) if c.label == "CDC, art. 4-A"]
    assert len(parts) > 1
    assert parts[1].text.startswith("CDC, art. 4-A (continuação):")
