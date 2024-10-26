import subprocess
import sys
import os
import hashlib
import anki
import pathlib
from aqt import mw
from aqt.qt import *
from aqt import gui_hooks

sys.path.insert(0, str(pathlib.Path(os.path.dirname(__file__)) / "libs"))
import marko

static_html = """
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css" integrity="sha384-nB0miv6/jRmo5UMMR1wu3Gz6NLsoTkbqJghGIsx//Rlm+ZU03BU6SQNC66uf4l5+" crossorigin="anonymous">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js" integrity="sha384-7zkQWkzuo3B5mTepMUcHkMB5jZaolc2xDwL6VFqjFALcbeS9Ggm/Yr2r3Dy4lfFg" crossorigin="anonymous"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js" integrity="sha384-43gviWU0YVjaDtb/GhzOouOXtZMP/7XUzwPTstBeZFe/+rCMvRwr4yROQP43s0Xk" crossorigin="anonymous" onload="renderMathInElement(document.body);"></script>
"""

col = mw.col
ext_pwd = pathlib.Path(os.path.dirname(__file__))
card_folder = ext_pwd / "cards/"
git_repo = "https://git.rheydskey.org/rheydskey/anki-md"


class Git:
    def __init__(self):
        self.cmd = "/usr/bin/git"

    def exe(self, *args: str):
        subprocess.run([self.cmd] + list(args))

    def clone(self, url: str):
        self.exe("clone", url, card_folder)


class Utils:
    def get_stripped_lines(s: str) -> [str]:
        buf = []
        for line in s.splitlines():
            strip = line.strip()
            if len(strip) != 0:
                buf.append(strip)

        return buf


class CardGenerator:
    def __init__(self, extend=False):
        self.marko = marko.Markdown()
        self.recto = ""
        self.verso = ""
        self.extend = extend
        self.hash_of_raw = None

    def fillBuffers(self, s: str):
        if self.extend:
            splitter_at = s.find("%")
            end_recto = s.rfind("\n", 0, splitter_at)
            start_verso = s.find("\n", splitter_at)
            self.recto = s[0:end_recto]
            self.verso = s[start_verso:]
        else:
            lines = s.splitlines()
            self.recto += lines[0]
            self.verso += "\n".join(lines[1:])

    def gen_note(self, s: str) -> (str, str):
        self.hash_of_raw = hashlib.sha512(bytes(s, "utf-8")).hexdigest()
        self.fillBuffers(s)
        return (self.marko.convert(self.recto), self.marko.convert(self.verso))

    def gen_note_with_hash(self, s: str):
        (recto, verso) = self.gen_note(s)
        return (recto, verso, self.hash_of_raw)


class DeckGenerator:
    def __init__(self, did: anki.decks.DeckId):
        self.did = did
        self.hash_notes = None

    def refresh_hash(self) -> None:
        notes = mw.col.find_notes(f"did:{self.did}")
        self.hash_notes = [mw.col.get_note(note).fields[2] for note in notes]

    def is_note_in_deck(self, s: str) -> bool:
        if self.hash_notes is None:
            self.refresh_hash()

        return hashlib.sha512(bytes(s, "utf-8")).hexdigest() in self.hash_notes

    def gen_decks(self, s: str) -> [(str, str, hash)]:
        gen = []
        buf = ""
        extend_body = False
        stripped_lines = Utils.get_stripped_lines(s)
        print(stripped_lines)
        for lines in stripped_lines:
            if lines.startswith("##"):
                if len(buf) != 0:
                    if not self.is_note_in_deck(buf):
                        gen.append(
                            CardGenerator(extend=extend_body).gen_note_with_hash(buf)
                        )

                extend_body = False
                buf = ""

            if lines.startswith("%"):
                extend_body = True
            buf += lines + "\n"

        if len(buf) != 0:
            if not self.is_note_in_deck(buf):
                gen.append(CardGenerator(extend=extend_body).gen_note_with_hash(buf))

        return gen


def init_deck(deck: anki.decks.Deck, folder: pathlib.Path):
    if not folder.is_dir():
        return
    for entry in folder.iterdir():
        filename, fileext = os.path.splitext(entry)
        if entry.is_file() and fileext == ".md":
            print(entry)
            with open(entry, "r") as file:
                deck_gen = DeckGenerator(deck["id"])
                for recto, verso, hash in deck_gen.gen_decks(file.read()):
                    model = mw.col.models.all()[0]
                    note = mw.col.new_note(model["id"])
                    note.fields[0] = recto
                    note.fields[1] = verso
                    note.fields[2] = hash

                    mw.col.add_note(note, deck["id"])

    return


def create_model():
    model = mw.col.models.new("Ankill")
    recto = mw.col.models.new_field("Recto")
    mw.col.models.add_field(model, recto)
    verso = mw.col.models.new_field("Verso")
    mw.col.models.add_field(model, verso)
    hash = mw.col.models.new_field("Hash")
    hash["collapsed"] = True
    mw.col.models.add_field(model, hash)
    template = mw.col.models.new_template("Carte")
    template["qfmt"] = "{{Recto}}" + static_html
    template["afmt"] = "{{FrontSide}}\n\n<hr id=answer>\n\n{{Verso}}"
    mw.col.models.add_template(model, template)
    return model


def init() -> None:
    os.chdir(ext_pwd)
    if not os.path.isdir(card_folder):
        os.remove(card_folder)

    if not os.path.exists(card_folder):
        Git().clone(git_repo)

    deck = mw.col.decks.all()
    deck_name = [d["name"] for d in deck]

    if "Ankill" not in [n.name for n in mw.col.models.all_names_and_ids()]:
        mw.col.models.save(create_model())

    for folder in card_folder.iterdir():
        name = folder.name
        if folder.is_dir() and not name.startswith("."):
            if name not in deck_name:
                nd = mw.col.decks.new_deck()
                nd.name = name
                mw.col.decks.add_deck(nd)

            id = mw.col.decks.id_for_name(name)
            init_deck(mw.col.decks.get(id), folder)

    mw.deckBrowser.refresh()


gui_hooks.profile_did_open.append(init)
