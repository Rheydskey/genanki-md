import anki
import hashlib


def get_stripped_lines(s: str) -> [str]:
    return [line.strip() for line in s.splitlines()]


def is_extends(s: str):
    return any([i.startswith("%") for i in get_stripped_lines(s)])


def add_note_to_deck(notes: [(str, str, str)], mid: int, did: int, collection: anki.collection.Collection):
    """
        mid: Model id
        did: Deck id
    """
    for recto, verso, card_hash in notes:
        note = collection.new_note(mid)
        note.fields[0] = recto
        note.fields[1] = verso
        note.fields[2] = card_hash
        collection.add_note(note, did)


def hash_card(r, v):
    return hashlib.sha512(bytes(f"{r}{v}", "utf-8")).hexdigest()
