import anki
import hashlib
import marko

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
    def __init__(self, did: anki.decks.DeckId, mw):
        self.did = did
        self.hash_notes = None
        self.mw = mw

    def refresh_hash(self) -> None:
        notes = self.mw.col.find_notes(f"did:{self.did}")
        self.hash_notes = [self.mw.col.get_note(note).fields[2] for note in notes]

    def is_note_in_deck(self, s: str) -> bool:
        if self.hash_notes is None:
            self.refresh_hash()

        return hashlib.sha512(bytes(s, "utf-8")).hexdigest() in self.hash_notes

    def gen_decks(self, s: str) -> [(str, str, hash)]:
        gen = []
        buf = ""
        extend_body = False
        stripped_lines = Utils.get_stripped_lines(s)
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
