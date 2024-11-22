import sys
import os
import anki
import pathlib
import hashlib
from aqt import mw
from aqt.qt import *
from aqt import gui_hooks
from aqt.operations import QueryOp

sys.path.insert(0, str(pathlib.Path(os.path.dirname(__file__)) / "libs"))

from .gen_md import DeckGenerator
from .diff import Diff
from .git import Git
from .utils import get_stripped_lines
from .mdanki import MdAnkiMigrator

static_html = """
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css" integrity="sha384-nB0miv6/jRmo5UMMR1wu3Gz6NLsoTkbqJghGIsx//Rlm+ZU03BU6SQNC66uf4l5+" crossorigin="anonymous">
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js" integrity="sha384-7zkQWkzuo3B5mTepMUcHkMB5jZaolc2xDwL6VFqjFALcbeS9Ggm/Yr2r3Dy4lfFg" crossorigin="anonymous"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js" integrity="sha384-43gviWU0YVjaDtb/GhzOouOXtZMP/7XUzwPTstBeZFe/+rCMvRwr4yROQP43s0Xk" crossorigin="anonymous" onload="renderMathInElement(document.body);"></script>
"""

col = mw.col
ext_pwd = pathlib.Path(os.path.dirname(__file__))
card_folder = ext_pwd / "cards/"
git_repo = "https://git.rheydskey.org/rheydskey/anki-md"


def get_from_title(note_title, cards: [(str, str, any)]) -> int | None:
    print(list(map(lambda v: "\n".join(v[0]), cards)))
    try:
        return list(map(lambda v: "\n".join(v[0]).strip(), cards)).index(note_title.strip())
    except:
        return None


def convert(noteid, card, model):
    model = mw.col.models.by_name("Ankill")
    note = mw.col.get_note(noteid)

    old_notetype_id = note.note_type()["id"]
    new_notetype_id = model["id"]

    payload = mw.col.models.change_notetype_info(
        old_notetype_id=old_notetype_id, new_notetype_id=new_notetype_id
    )
    req = payload.input
    req.note_ids.extend([noteid])
    mw.col.models.change_notetype_of_notes(req)

    note = mw.col.get_note(noteid)

    note.fields[0] = "\n".join(card[0])
    note.fields[1] = "\n".join(card[1])
    note.fields[2] = card[2]

    mw.col.update_note(note)


def migrate_old_card(deck: anki.decks.Deck, folder: pathlib.Path):
    did = deck["id"]

    q = f"did:{did} -note:Ankill"
    notes = mw.col.find_notes(q)
    migrator = MdAnkiMigrator()
    notes_content = [
        (
            migrator.convert(mw.col.get_note(note).fields[0]),
            migrator.convert(mw.col.get_note(note).fields[1]),
        )
        for note in notes
    ]
    notes_hash = [
        hashlib.sha512(bytes(f"{r}{v}", "utf-8")).hexdigest()
        for (r, v) in notes_content
    ]

    if len(notes) == 0:
        return

    deck_gen = DeckGenerator(deck["id"], mw)
    cards = []
    for entry in folder.iterdir():
        filename, fileext = os.path.splitext(entry)
        if entry.is_file() and fileext == ".md":
            with open(entry, "r") as file:
                cards.extend(
                    list(
                        map(
                            lambda r: (
                                get_stripped_lines(r[0]),
                                get_stripped_lines(r[1]),
                                r[2],
                            ),
                            deck_gen.gen_decks(file.read()),
                        )
                    )
                )

    card_hash = [
        hashlib.sha512(
            bytes(
                f"{"\n".join(r)}{"\n".join(v)}",
                "utf-8",
            )
        ).hexdigest()
        for (r, v, _) in cards
    ]
    print(cards)
    print(notes_content)

    n = 0
    for n, note_hash in enumerate(notes_hash):
        print(f"{n} {note_hash}")
        if note_hash in card_hash:
            card = cards[card_hash.index(note_hash)]
            convert(notes[n], card, mw.col.models.by_name("Ankill"))
        else:
            print(notes_content[n][0])
            last_try = get_from_title(notes_content[n][0], cards)
            print(last_try)
            if last_try is not None:
                convert(notes[n], cards[last_try], mw.col.models.by_name("Ankill"))
                print("Last is always good")


def init_deck(deck: anki.decks.Deck, folder: pathlib.Path):
    if not folder.is_dir():
        return

    migrate_old_card(deck, folder)
    for entry in folder.iterdir():
        filename, fileext = os.path.splitext(entry)
        if entry.is_file() and fileext == ".md":
            with open(entry, "r") as file:
                deck_gen = DeckGenerator(deck["id"], mw)
                for recto, verso, hash in deck_gen.gen_decks(file.read()):
                    model = mw.col.models.by_name("Ankill")
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
    os.chdir(ext_pwd)

    if not os.path.exists(card_folder):
        Git().clone(git_repo, card_folder)

    if not os.path.isdir(card_folder):
        os.remove(card_folder)
        Git().clone(git_repo, card_folder)

    os.chdir(card_folder)

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
