from anki.decks import DeckDict
from unidiff import PatchedFile, PatchSet
from .git import Git
from .gen_md import CardGenerator, DeckGenerator
from .utils import get_stripped_lines, is_extends, add_note_to_deck
from aqt import mw
import anki
from typing import Union
import hashlib


def get_note_of_scope(source: str, nth) -> Union[str, None]:
    """
    Return the note that contains nth line
    """
    lines = source.splitlines()
    if len(lines) < nth:
        return None

    start_line = None
    for n, i in enumerate(lines[0: nth + 1]):
        if i.startswith("##"):
            start_line = n

    if start_line is None:
        return None

    end_line = None
    for n, i in enumerate(lines[nth + 1:]):
        if i.startswith("##"):
            end_line = n

    if end_line is None:
        return "\n".join(lines[start_line:])

    return "\n".join(lines[start_line: (start_line + end_line)])


def create_note(s: str, deckid, model):
    note = mw.col.new_note(model["id"])

    recto, verso, hash = CardGenerator(extend=is_extends(s)).gen_note_with_hash(s)

    note.fields[0] = recto
    note.fields[1] = verso
    note.fields[2] = hash
    mw.col.add_note(note, deckid)


class DeleteFile:
    def __init__(self, from_source: str, deck: DeckDict, collection: anki.collection.Collection):
        self.from_source = from_source
        self.deckid = deck["id"]
        self.collection = collection

    def _delete_one(self, source: str):
        stripped_lines = get_stripped_lines(source)
        hash = hashlib.sha512(bytes("\n".join(stripped_lines), "utf-8")).hexdigest()
        q = f"hash:{hash} did:{self.deckid} "
        self.collection.remove_notes(self.collection.find_notes(q))

    def delete(self):
        for i in self.from_source.split("##"):
            self._delete_one("##" + i)


class ModifiedFile:
    def __init__(
        self, from_source: str, to_source: str, diff: PatchedFile, deck: DeckDict,
        collection: anki.collection.Collection
    ):
        self.from_source = from_source
        self.to_source = to_source
        self.diff = diff
        self.deckid = deck["id"]
        self.collection = collection

    def _update(self, from_note, to_note):
        stripped_lines = get_stripped_lines(from_note)
        hash = hashlib.sha512(bytes("\n".join(stripped_lines), "utf-8")).hexdigest()
        q = f"hash:{hash} did:{self.deckid}"
        notes = self.collection.find_notes(q)

        if len(notes) == 0:
            return

        unote = self.collection.get_note(notes[0])
        (recto, verso, hash) = CardGenerator(
            extend=is_extends(to_note)
        ).gen_note_with_hash(to_note)
        unote.fields[0] = recto
        unote.fields[1] = verso
        unote.fields[2] = hash
        self.collection.update_note(unote)

    def _update_one(self, hunk):
        from_note = get_note_of_scope(self.from_source, hunk.source_start)
        to_note = get_note_of_scope(self.to_source, hunk.target_start)
        self._update(from_note, to_note)

    def __is_all_deleted_line(self, lines: [any]):
        return all([i.is_removed for i in lines])

    def __is_all_added_line(self, lines: [any]):
        return all([i.is_removed for i in lines])

    def create_or_update_note(self, lines: [any], start_line: int, model) -> None:
        # FIXME: Remove stripped line and strip on value. Side-effect ?
        str_lines = get_stripped_lines("\n".join([f.value for f in lines]))
        if len(str_lines) == 0:
            return

        if self.__is_all_deleted_line(lines):
            note = get_note_of_scope(self.from_source, start_line)
            DeleteFile(note, self.collection.decks.get(self.deckid)["name"]).delete()
            return

        if self.__is_all_added_line(lines):
            unote = get_note_of_scope(self.to_source, start_line)

            create_note(unote, self.deckid, model)
            return

        note = get_note_of_scope(self.from_source, start_line)
        unote = get_note_of_scope(self.to_source, start_line)
        self._update(note, unote)
        return

    def update(self):
        model = self.collection.models.by_name("Ankill")
        for hunk in self.diff:
            start_line = hunk.target_start
            buf = []
            for line in hunk:
                if line.value.startswith("##"):
                    if len(buf) != 0:
                        self.create_or_update_note(buf, start_line, model)
                        start_line += len(buf)
                        buf = []
                buf.append(line)

            if len(buf) != 0:
                self.create_or_update_note(buf, start_line, model)


class Diff:
    def __init__(self, rev_from: str, rev_to: str, collection: anki.collection.Collection):
        self.rev_from = rev_from
        self.rev_to = rev_to
        self.collection = collection

    def update_deck_and_notes(self):
        for i in PatchSet(Git().diff(self.rev_from, self.rev_to)):
            deck_name = i.path.split("/")[0]
            deck = self.collection.decks.by_name(deck_name)
            if not i.path.endswith(".md"):
                continue

            if i.is_added_file and not i.is_rename:
                notes_source = Git().show(self.rev_to, i.path)
                model = self.collection.models.by_name("Ankill")
                notes = DeckGenerator(deck["id"], self.collection).gen_decks(notes_source)
                add_note_to_deck(notes, model["id"], deck["id"], self.collection)

            if i.is_removed_file and not i.is_rename:
                from_source = Git().show(self.rev_from, i.path)
                DeleteFile(from_source, deck, self.collection).delete()

            if i.is_modified_file:
                from_source = Git().show(self.rev_from, i.path)
                to_source = Git().show(self.rev_to, i.path)
                ModifiedFile(from_source, to_source, i, deck, self.collection).update()
