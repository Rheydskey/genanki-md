import sys
import os
import anki
import pathlib
from aqt import mw, gui_hooks
from aqt.utils import showWarning
from aqt.operations import QueryOp

sys.path.insert(0, str(pathlib.Path(os.path.dirname(__file__)) / "libs"))

from .gen_md import DeckGenerator
from .diff import Diff
from .git import Git
from .migrator import migrate_old_card

static_html = """
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css" integrity="sha384-nB0miv6/jRmo5UMMR1wu3Gz6NLsoTkbqJghGIsx//Rlm+ZU03BU6SQNC66uf4l5+" crossorigin="anonymous">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js" integrity="sha384-7zkQWkzuo3B5mTepMUcHkMB5jZaolc2xDwL6VFqjFALcbeS9Ggm/Yr2r3Dy4lfFg" crossorigin="anonymous"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js" integrity="sha384-43gviWU0YVjaDtb/GhzOouOXtZMP/7XUzwPTstBeZFe/+rCMvRwr4yROQP43s0Xk" crossorigin="anonymous" onload="renderMathInElement(document.body);"></script>
"""

addon_path = pathlib.Path(os.path.dirname(__file__))
# https://addon-docs.ankiweb.net/addon-config.html#user-files
user_files = addon_path / "user_files"
card_folder = user_files / "cards/"
git_repo = "__YOUR_REPO__"


def init_deck(deck: anki.decks.Deck, folder: pathlib.Path):
    if not folder.is_dir():
        return

    migrate_old_card(deck, folder)
    model = mw.col.models.by_name("Ankill")
    deck_gen = DeckGenerator(deck["id"], mw)
    for entry in folder.iterdir():
        filename, fileext = os.path.splitext(entry)
        if entry.is_file() and fileext == ".md":
            with open(entry, "r") as file:
                for recto, verso, hash in deck_gen.gen_decks(file.read()):
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


def update_repo(e):
    os.chdir(card_folder)
    pull = Git().pull()
    if not pull.startswith("Updat"):
        print("No update. Nice no work to do so")
        return

    lines = pull.splitlines()

    update = lines[0]
    rev_from, rev_to = update.strip("Updating ").split("..")
    return (rev_from, rev_to)


def refresh_card(x):
    if x is None:
        return
    (rev_from, rev_to) = x
    Diff(rev_from, rev_to).update_deck_and_notes()


def init() -> None:
    if git_repo == "__YOUR_REPO__":
        showWarning("Please change the url of your git repo")
        return

    # Initialize user_files folder
    if not os.path.exists(user_files):
        os.makedirs(user_files)
    elif not os.path.isdir(user_files):
        os.makedirs(user_files)
        os.remove(user_files)

    if not os.path.exists(card_folder):
        Git().clone(git_repo, card_folder)
    elif not os.path.isdir(card_folder):
        os.remove(card_folder)
        Git().clone(git_repo, card_folder)

    mw.create_backup_now()

    deck = mw.col.decks.all()
    deck_name = [d["name"].lower() for d in deck]

    if "Ankill" not in [n.name for n in mw.col.models.all_names_and_ids()]:
        mw.col.models.save(create_model())

    for folder in card_folder.iterdir():
        name = folder.name.lower()
        if folder.is_dir() and not name.startswith("."):
            if name not in deck_name:
                nd = mw.col.decks.new_deck()
                nd.name = name
                mw.col.decks.add_deck(nd)

            id = mw.col.decks.id_for_name(name)
            init_deck(mw.col.decks.get(id), folder)

    op = QueryOp(
        parent=mw,
        op=update_repo,
        success=refresh_card,
    )

    op.with_progress(label="Update git repo").run_in_background()
    mw.deckBrowser.refresh()


gui_hooks.profile_did_open.append(init)
