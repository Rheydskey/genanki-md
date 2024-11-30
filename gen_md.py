import anki
import hashlib
import marko
from .utils import get_stripped_lines


class CardGenerator:
    def __init__(self, extend=False):
        self.marko = marko.Markdown()
        self.recto = ""
        self.verso = ""
        self.extend = extend

    def fill_buffers(self, s: str):
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
        self.fill_buffers(s)
        return (self.marko.convert(self.recto), self.marko.convert(self.verso))

    def gen_note_with_hash(self, s: str):
        hash_of_raw = hashlib.sha512(bytes(s, "utf-8")).hexdigest()
        (recto, verso) = self.gen_note(s)
        return (recto, verso, hash_of_raw)


class DeckGenerator:
    def __init__(self, did: anki.decks.DeckId, mw):
        self.did = did
        self.hash_notes = None
        self.mw = mw

    def refresh_hash(self) -> None:
        note_ids = self.mw.col.find_notes(f"did:{self.did} note:Ankill")
        notes = [self.mw.col.get_note(id) for id in note_ids]
        self.hash_notes = [note.fields[2] for note in notes if len(note.fields) >= 3]

    def is_note_in_deck(self, s: str) -> bool:
        if self.hash_notes is None:
            self.refresh_hash()

        # Hash should always be an hash of the input lines of card not of the generated html
        return hashlib.sha512(bytes(s, "utf-8")).hexdigest() in self.hash_notes

    def get_md_cards(self, lines: [str]) -> [[str]]:
        buf = []
        card = []
        for line in lines:
            if line.startswith("##") and len(card) != 0:
                buf.append(card)
                card = []
            card.append(line)
        if len(card) != 0:
            buf.append(card)
        return buf

    def is_extend_body(self, lines: [str]) -> bool:
        return any([line.startswith("%") for line in lines])

    def gen_decks(self, s: str) -> [(str, str, hash)]:
        gen_cards = []
        stripped_lines = get_stripped_lines(s)
        cards = self.get_md_cards(stripped_lines)

        for card in cards:
            extend_body = self.is_extend_body(card)
            lines = "\n".join(card)
            if not self.is_note_in_deck(lines):
                card = CardGenerator(extend=extend_body).gen_note_with_hash(lines)
                gen_cards.append(card)

        return gen_cards
