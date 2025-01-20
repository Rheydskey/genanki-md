from src.gen_md import CardGenerator


def test_basic():
    recto, verso = CardGenerator().gen_note("""## test
content
""")
    print(recto)
    print(verso)
    assert recto == "<h2>test</h2>\n" and verso == "<p>content</p>\n"


def test_math():
    recto, verso = CardGenerator().gen_note("""## test
$$ \\begin{matrix} a & b \\\\ c & d \\end{matrix} $$
""")
    print(recto)
    print(verso)
    assert recto == "<h2>test</h2>\n" and verso == "<p>$$ \\begin{matrix} a & b \\\\ c & d \\end{matrix} $$</p>\n"
