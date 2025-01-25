import os
import pathlib
import shutil
import subprocess
import hashlib
from anki.collection import Collection
from src.diff import get_note_of_scope
from src.gen_md import CardGenerator, DeckGenerator
from src import create_model, add_note_to_deck, create_decks, fill_decks, refresh_card
from src.utils import get_stripped_lines, is_extends
from src.migrator import migrate_old_card

basic_input = """## Blahaj
A lovely shark"""


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


class FakeFolder:
    def __init__(self):
        self.path = "./fake_folder"

    def __enter__(self):
        e = pathlib.Path(self.path)
        source = """## test
eeee"""
        os.mkdir(e)
        os.mkdir(e / "fcard")
        with open(e / "fcard" / "card.md", "x") as f:
            f.write(source)

        os.mkdir(e / "vcard")
        with open(e / "vcard" / "card.md", "x") as f:
            f.write(source)

        return e

    def __exit__(self, *args):
        shutil.rmtree(self.path)


class TempPwd:
    def __init__(self, path):
        self.path = path

    def __enter__(self):
        self.current = os.path.abspath(os.getcwd())
        os.chdir(self.path)
        return None

    def __exit__(self, *args):
        os.chdir(self.current)


class FakeGitRepo:
    def __init__(self):
        self.path = "./fake_git_repo"

    def __enter__(self):
        os.mkdir(pathlib.Path(self.path))
        with TempPwd(self.path):
            p = subprocess.run(["git", "init"])
            print(p.stdout)

        return pathlib.Path(self.path)

    def __exit__(self, *args):
        shutil.rmtree(self.path)


class GitHandler:
    def __init__(self, path):
        self.path = path

    def commit(self, files: [str], msg: str):
        with TempPwd(self.path) as _:
            p = subprocess.run(["git", "add"] + files, capture_output=True)
            p = subprocess.run(["git", "commit", "-m", msg], capture_output=True)
            print(p.stdout)

    def log(self) -> str:
        with TempPwd(self.path) as _:
            p = subprocess.run(["git", "--no-pager", "log"], capture_output=True)
            return p.stdout.decode("utf-8")


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


def test_table():
    recto, verso = CardGenerator().gen_note("""## test
| P   | ¬P  |
|-----|-----|
|  0  |  1  |
|  1  |  0  |
""")
    print(recto)
    print(verso)
    assert recto == "<h2>test</h2>\n"
    assert (
        verso
        == """<table>
<thead>
<tr>
<th>P</th>
<th>¬P</th>
</tr>
</thead>
<tbody>
<tr>
<td>0</td>
<td>1</td>
</tr>
<tr>
<td>1</td>
<td>0</td>
</tr>
</tbody></table>"""
    )


def test_hash():
    recto, verso, hash = CardGenerator().gen_note_with_hash("""## test
$$ a = b $$
""")
    print(recto)
    print(verso)
    print(hash)
    assert recto == "<h2>test</h2>\n"
    assert verso == "<p>$$ a = b $$</p>\n"
    assert hash == (
        "2947533de7947e99abfc3dce9c18519321118d9e14bea6efd14dc701d"
        + "dafb65ab69db2ebf0c7d3d60145be9fee014edfaac32ce1f38e859f"
        + "4599ec9f09fdd595"
    )


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


def test_note_of_scope_too_far():
    source = """## Card
cards"""

    a = get_note_of_scope(source, 30)
    assert a is None


def test_note_of_scope_with_no_note():
    # https://www.reddit.com/r/copypasta/comments/15mkg2b/im_a_skibidi_toilet_with_the_grimace_shake_in_ohio/
    source = """im a skibidi toilet with the grimace shake in ohio
with maximum sigma male gigachad big chungus doing the goofy
ahh griddy with my garten of banban rizz while Monday left me
broken when i was playing pizza tower Friday night fukin epic
roblox moment skibidi bop bop bop yes yes while screaming as
pizza tower charachters cause im gonna sauce you up nuh uh,
im a skibidi toilet maximum ohio rizz with the sauce rizz you
up l + ratio epic gamer number lore bussin sigma male skibidi
bop bop mr beeeaast lightskin scare grimace shake pizza tower
screaming boykisser furry slayer moment gamer!!!!!!!
oh my among us! you just activated my ultimate ohio sus Friday
night funkin oklahoma powers epicly i will lightskin stare at
you till you combust into a million memes and i will get my
ohio revenge!"""

    a = get_note_of_scope(source, 0)
    assert a is None


def test_note_of_scope_multi_note():
    source = """## Card1
card1

## Card2
card2
"""
    first = get_note_of_scope(source, 0)
    assert (
        first
        == """## Card1
card1"""
    )
    second = get_note_of_scope(source, 3)
    assert (
        second
        == """## Card2
card2"""
    )


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


def test_create_deck():
    with FakeAnki() as collection:
        with FakeFolder() as folder:
            create_decks(folder, [], collection)
        # Decks from folders + default deck of anki
        # 2 + 1 = 3
        assert len(collection.decks.all()) == 3


def test_fill_deck():
    with FakeAnki() as collection:
        with FakeFolder() as folder:
            collection.models.save(create_model(collection))
            create_decks(folder, [], collection)
            fill_decks(folder, [], collection)
        for i in collection.decks.all_names_and_ids():
            if i.name == "Default":
                continue

            assert len(collection.find_notes(f"did:{i.id}")) == 1


def test_diff_check():
    with FakeAnki() as collection:
        with FakeGitRepo() as folder:
            collection.models.save(create_model(collection))
            git = GitHandler(folder)

            os.mkdir(folder / "fcard")
            with open(folder / "fcard" / "card.md", "x") as f:
                f.write(basic_input)

            git.commit(["."], "initial commit")

            create_decks(folder, [], collection)
            fill_decks(folder, [], collection)

            with open(folder / "fcard" / "card.md", "a") as f:
                f.write("ee")

            git.commit(["."], "Update note")
            lines = [
                line.lstrip("commit ")
                for line in git.log().splitlines()
                if line.startswith("commit")
            ]
            from_commit, to_commit = lines[1][0:6], lines[0][0:6]
            with TempPwd(folder):
                refresh_card((from_commit, to_commit), collection=collection)

        deckdict = collection.decks.by_name("fcard")
        did = deckdict["id"]
        for i in collection.find_notes(f"did:{did}"):
            fields = collection.get_note(i).fields
            assert fields[0] == "<h2>Blahaj</h2>\n"
            assert fields[1] == "<p>A lovely sharkee</p>\n"


def test_diff_remove():
    with FakeAnki() as collection:
        with FakeGitRepo() as folder:
            collection.models.save(create_model(collection))
            git = GitHandler(folder)

            os.mkdir(folder / "fcard")
            with open(folder / "fcard" / "card.md", "x") as f:
                f.write(basic_input)

            git.commit(["."], "initial commit")

            create_decks(folder, [], collection)
            fill_decks(folder, [], collection)

            os.remove(folder / "fcard" / "card.md")
            git.commit(["."], "Update note")
            lines = [
                line.lstrip("commit ")
                for line in git.log().splitlines()
                if line.startswith("commit")
            ]
            from_commit, to_commit = lines[1][0:6], lines[0][0:6]
            with TempPwd(folder):
                refresh_card((from_commit, to_commit), collection=collection)

        deckdict = collection.decks.by_name("fcard")
        did = deckdict["id"]

        assert len(collection.find_notes(f"did:{did}")) == 0


def test_diff_add_file():
    with FakeAnki() as collection:
        with FakeGitRepo() as folder:
            collection.models.save(create_model(collection))
            git = GitHandler(folder)

            os.mkdir(folder / "fcard")
            with open(folder / "fcard" / "card.md", "x") as f:
                f.write(basic_input)

            git.commit(["."], "initial commit")

            create_decks(folder, [], collection)
            fill_decks(folder, [], collection)

            with open(folder / "fcard" / "card1.md", "x") as f:
                f.write(basic_input + "ee")

            git.commit(["."], "Update note")
            lines = [
                line.lstrip("commit ")
                for line in git.log().splitlines()
                if line.startswith("commit")
            ]
            from_commit, to_commit = lines[1][0:6], lines[0][0:6]
            with TempPwd(folder):
                refresh_card((from_commit, to_commit), collection=collection)

        deckdict = collection.decks.by_name("fcard")
        did = deckdict["id"]

        assert len(collection.find_notes(f"did:{did}")) == 2


def test_mdanki_migration():
    with FakeAnki() as collection:
        with FakeFolder() as folder:
            os.mkdir(folder / "test")
            with open(folder / "test" / "patch-1.md", "w") as file:
                file.write(basic_input)
            collection.models.save(create_model(collection))
            deck_test = collection.decks.new_deck()
            deck_test.name = "test"
            collection.decks.add_deck(deck_test)
            deck_test = collection.decks.by_name("test")
            basic = collection.models.by_name("Basic")
            note = collection.new_note(basic["id"])
            note.fields[0] = '<h2 id="blahaj">Blahaj</h2>'
            note.fields[1] = "<p>A lovely shark</p>"
            collection.add_note(note, deck_test["id"])
            migrate_old_card(deck_test, folder / "test", collection)

            for i in collection.find_cards(f"did:{deck_test['id']}"):
                c = collection.get_card(i)
                nt = c.note().note_type()
                assert nt["name"] == "Ankill"
                assert (
                    c.note().values()[2]
                    == hashlib.sha512(bytes(basic_input, "utf-8")).hexdigest()
                )


def test_mdanki_migration_with_br():
    input = """## Blahaj
A lovely shark

aa
a
a
a
a
aa"""

    with FakeAnki() as collection:
        with FakeFolder() as folder:
            os.mkdir(folder / "test")
            with open(folder / "test" / "patch-1.md", "w") as file:
                file.write(input)
            collection.models.save(create_model(collection))
            deck_test = collection.decks.new_deck()
            deck_test.name = "test"
            collection.decks.add_deck(deck_test)
            deck_test = collection.decks.by_name("test")
            basic = collection.models.by_name("Basic")
            note = collection.new_note(basic["id"])
            note.fields[0] = '<h2 id="blahaj">Blahaj</h2>'
            note.fields[1] = """<p>A lovely shark</p>
<p>aa<br>a<br>a<br>a<br>a<br>aa</p>"""
            collection.add_note(note, deck_test["id"])
            migrate_old_card(deck_test, folder / "test", collection)

            print(CardGenerator().gen_note(input))

            for i in collection.find_cards(f"did:{deck_test['id']}"):
                c = collection.get_card(i)
                nt = c.note().note_type()
                assert nt["name"] == "Ankill"
                assert (
                    c.note().values()[2]
                    == hashlib.sha512(bytes(input, "utf-8")).hexdigest()
                )


def test_mdanki_migration_with_slash():
    input = """## Blahaj
A lovely shark
eeee \\\\"""

    with FakeAnki() as collection:
        with FakeFolder() as folder:
            os.mkdir(folder / "test")
            with open(folder / "test" / "patch-1.md", "w") as file:
                file.write(input)
            collection.models.save(create_model(collection))
            deck_test = collection.decks.new_deck()
            deck_test.name = "test"
            collection.decks.add_deck(deck_test)
            deck_test = collection.decks.by_name("test")
            basic = collection.models.by_name("Basic")
            note = collection.new_note(basic["id"])
            note.fields[0] = '<h2 id="blahaj">Blahaj</h2>'
            note.fields[1] = """<p>A lovely shark<br>eeee \\</p>"""
            collection.add_note(note, deck_test["id"])
            migrate_old_card(deck_test, folder / "test", collection)

            print(CardGenerator().gen_note(input))

            for i in collection.find_cards(f"did:{deck_test['id']}"):
                c = collection.get_card(i)
                nt = c.note().note_type()
                assert nt["name"] == "Ankill"
                assert (
                    c.note().values()[2]
                    == hashlib.sha512(bytes(input, "utf-8")).hexdigest()
                )
