import os
import anki
import pathlib
from typing import Union
from .gen_md import DeckGenerator
from .utils import get_stripped_lines, hash_card
from .migrators.mdanki import MdAnkiMigrator


def get_from_title(note_title: str, cards: [(str, str, any)]) -> Union[int, None]:
    note_titles = ["\n".join(r).strip() for (r, _, _) in cards]
    try:
        return note_titles.index(note_title.strip())
    except ValueError:
        return None


def get_converted_content_of_note(note, migrator, collection):
    return (
        migrator.convert(collection.get_note(note).fields[0]),
        migrator.convert(collection.get_note(note).fields[1]),
    )


def strip_card(card):
    return get_stripped_lines(card[0]), get_stripped_lines(card[1]), card[2]


def gen_and_strip(input, gen):
    return list(map(strip_card, gen.gen_decks(input)))


def convert(noteid, card, modelid, collection):
    note = collection.get_note(noteid)
    old_notetype_id = note.note_type()["id"]

    req = collection.models.change_notetype_info(
        old_notetype_id=old_notetype_id, new_notetype_id=modelid
    ).input
    req.note_ids.append(noteid)

    collection.models.change_notetype_of_notes(req)

    note = collection.get_note(noteid)

    note.fields[0] = "\n".join(card[0])
    note.fields[1] = "\n".join(card[1])
    note.fields[2] = card[2]

    collection.update_note(note)


def migrate_old_card(deck: anki.decks.Deck, folder: pathlib.Path, collection: anki.collection.Collection):
    did = deck["id"]

    q = f"-note:Ankill did:{did}"
    notes = collection.find_notes(q)
    migrator = MdAnkiMigrator()
    notes_content = [get_converted_content_of_note(note, migrator, collection) for note in notes]
    notes_hash = [hash_card(r, v) for (r, v) in notes_content]

    if len(notes) == 0:
        return

    deck_gen = DeckGenerator(deck["id"], collection)
    cards = []
    for entry in folder.iterdir():
        filename, fileext = os.path.splitext(entry)
        if entry.is_file() and fileext == ".md":
            with open(entry, "r") as file:
                cards.extend(gen_and_strip(file.read(), deck_gen))

    card_hash = [hash_card("\n".join(r), "\n".join(v)) for (r, v, _) in cards]

    model = collection.models.by_name("Ankill")
    for n, note_hash in enumerate(notes_hash):
        if note_hash in card_hash:
            card = cards[card_hash.index(note_hash)]
            convert(notes[n], card, model["id"], collection)
        else:
            last_try = get_from_title(notes_content[n][0], cards)
            if last_try is not None:
                convert(notes[n], cards[last_try], model["id"], collection)
            else:
                print(f"Cannot migrate {notes[n]}")
