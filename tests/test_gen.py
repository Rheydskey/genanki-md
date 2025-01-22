import os
from anki.collection import Collection
from src.diff import get_note_of_scope
from src.gen_md import CardGenerator, DeckGenerator
from src import create_model, add_note_to_deck
from src.utils import get_stripped_lines, is_extends


class FakeAnki:
    def __init__(self):
        self.path = "./test_collection"
        self.col = None

    def __enter__(self):
        self.col = Collection(self.path)
        return self.col

    def __exit__(self, *args):
        self.col.close()
        os.remove(self.path)


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


def test_extend():
    source = """## What is this ?
Define what is a blahaj
%
A blahaj is a shark
"""
    recto, verso, hash = CardGenerator(extend=True).gen_note_with_hash(source)
    print(recto)
    print(verso)
    print(hash)
    assert recto == "<h2>What is this ?</h2>\n<p>Define what is a blahaj</p>\n"
    assert verso == "<p>A blahaj is a shark</p>\n"


def test_is_model_is_serializable():
    with FakeAnki() as col:
        print(col)
        model = create_model(col)
        import json
        json.dumps(model)


def test_note_of_scope_one_note():
    source = """## Card
cards"""

    a = get_note_of_scope(source, 0)
    assert a == source


def test_note_of_scope_multi_note():
    source = """## Card1
card1

## Card2
card2
"""
    first = get_note_of_scope(source, 0)
    assert first == """## Card1
card1"""
    second = get_note_of_scope(source, 3)
    assert second == """## Card2
card2"""


def test_is_extends():
    source = """## Card
the shark
%%
blahaj"""

    assert is_extends(source)


def test_is_extends_not():
    source = """## Card
blahaj"""

    assert not is_extends(source)


def test_stripped_lines():
    source = """             ## Card
         blahaj
"""
    assert get_stripped_lines(source) == ["## Card", "blahaj"]


def test_deck_generator():
    source = """## Blahaj
the shark
## The boykisser
a silly cat
    """
    with FakeAnki() as collection:
        create_model(collection)
        d = collection.decks.new_deck()
        d.name = "test"
        collection.decks.add_deck(d)
        id = collection.decks.id_for_name("test")
        dg = DeckGenerator(id, collection)
        cards = dg.gen_decks(source)
        # TODO: ADD HASHES OF SOURCE
        assert cards[0][0] == "<h2>Blahaj</h2>\n"
        assert cards[0][1] == "<p>the shark</p>\n"

        assert cards[1][0] == "<h2>The boykisser</h2>\n"
        assert cards[1][1] == "<p>a silly cat</p>\n"


def test_deck_generator_check_added():
    source = """## Blahaj
the shark
## The boykisser
a silly cat
    """
    with FakeAnki() as collection:
        collection.models.save(create_model(collection))
        mid = collection.models.by_name("Ankill")
        d = collection.decks.new_deck()
        d.name = "test"
        collection.decks.add_deck(d)
        id = collection.decks.id_for_name("test")
        print(id)
        dg = DeckGenerator(id, collection)
        cards = dg.gen_decks(source)
        add_note_to_deck(cards, mid, id, collection)
        print(collection.find_notes(f"did:{id}"))
        assert collection.note_count() == 2
