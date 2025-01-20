from src.gen_md import CardGenerator


def test_basic():
    recto, verso = CardGenerator().gen_note("""## test
content
""")
    print(recto)
    print(verso)
    assert recto == "<h2>test</h2>\n"
    assert verso == "<p>content</p>\n"


def test_math():
    recto, verso = CardGenerator().gen_note("""## test
$$ \\begin{matrix} a & b \\\\ c & d \\end{matrix} $$
""")
    print(recto)
    print(verso)
    assert recto == "<h2>test</h2>\n"
    assert verso == "<p>$$ \\begin{matrix} a & b \\\\ c & d \\end{matrix} $$</p>\n"


def test_math2():
    recto, verso = CardGenerator().gen_note("""## test
$$ a = b $$
""")
    print(recto)
    print(verso)
    assert recto == "<h2>test</h2>\n"
    assert verso == "<p>$$ a = b $$</p>\n"


def test_hash():
    recto, verso, hash = CardGenerator().gen_note_with_hash("""## test
$$ a = b $$
""")
    print(recto)
    print(verso)
    print(hash)
    assert recto == "<h2>test</h2>\n"
    assert verso == "<p>$$ a = b $$</p>\n"
    assert hash == ("2947533de7947e99abfc3dce9c18519321118d9e14bea6efd14dc701d"
                    + "dafb65ab69db2ebf0c7d3d60145be9fee014edfaac32ce1f38e859f"
                    + "4599ec9f09fdd595")
