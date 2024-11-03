from .git import Git
import sys
import os

import anki
import pathlib
from aqt import mw
from aqt.qt import *
from aqt import gui_hooks

sys.path.insert(0, str(pathlib.Path(os.path.dirname(__file__)) / "libs"))

from .gen_md import DeckGenerator
from .diff import Diff

static_html = """
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css" integrity="sha384-nB0miv6/jRmo5UMMR1wu3Gz6NLsoTkbqJghGIsx//Rlm+ZU03BU6SQNC66uf4l5+" crossorigin="anonymous">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js" integrity="sha384-7zkQWkzuo3B5mTepMUcHkMB5jZaolc2xDwL6VFqjFALcbeS9Ggm/Yr2r3Dy4lfFg" crossorigin="anonymous"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js" integrity="sha384-43gviWU0YVjaDtb/GhzOouOXtZMP/7XUzwPTstBeZFe/+rCMvRwr4yROQP43s0Xk" crossorigin="anonymous" onload="renderMathInElement(document.body);"></script>
"""

col = mw.col
ext_pwd = pathlib.Path(os.path.dirname(__file__))
card_folder = ext_pwd / "cards/"
git_repo = "https://git.rheydskey.org/rheydskey/anki-md"


def init_deck(deck: anki.decks.Deck, folder: pathlib.Path):
    if not folder.is_dir():
        return
    for entry in folder.iterdir():
        filename, fileext = os.path.splitext(entry)
        if entry.is_file() and fileext == ".md":
            print(entry)
            with open(entry, "r") as file:
                deck_gen = DeckGenerator(deck["id"], mw)
                for recto, verso, hash in deck_gen.gen_decks(file.read()):
                    model = mw.col.models.all()[0]
                    note = mw.col.new_note(model["id"])
                    note.fields[0] = recto
                    note.fields[1] = verso
                    note.fields[2] = hash
                    mw.col.add_note(note, deck["id"])


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

def le(f):
	mw.bottomWeb.setHtml(f"{f}<h1>SKIBILI</h1>")



def init() -> None:
    os.chdir(ext_pwd)

    if not os.path.exists(card_folder):
        Git().clone(git_repo, card_folder)

    if not os.path.isdir(card_folder):
        os.remove(card_folder)
        Git().clone(git_repo, card_folder)

    os.chdir(card_folder)

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

    pull = Git().pull()
    if pull.startswith("Updat"):
        lines = pull.splitlines()

        update = lines[0]
        rev_from, rev_to = update.strip("Updating ").split("..")
        Diff(rev_from, rev_to).update_deck_and_notes()
    else:
        print("No update. Nice no work to do so")

    mw.deckBrowser.refresh()
    print(mw.bottomWeb.page().toHtml(le))


gui_hooks.profile_did_open.append(init)
