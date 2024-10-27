from unidiff import PatchedFile, PatchSet
from .git import Git
from .gen_md import CardGenerator
from aqt import mw
import hashlib


def get_note_of_scope(source: str, line) -> str:
    """
    Return the note that we are in
    """
    lines = source.splitlines()
    start_line = None
    for n, i in enumerate(lines[0 : line + 1]):
        if i.startswith("##"):
            start_line = n
    end_line = None
    for n, i in enumerate(lines[line + 1 :]):
        if i.startswith("##"):
            end_line = n

    return "\n".join(lines[start_line:end_line])


def get_stripped_lines(s: str) -> [str]:
    buf = []
    for line in s.splitlines():
        strip = line.strip()
        if len(strip) != 0:
            buf.append(strip)

    return buf


class ModifiedFile:
    def __init__(
        self, from_source: str, to_source: str, diff: PatchedFile, deck_name: str
    ):
        self.from_source = from_source
        self.to_source = to_source
        self.diff = diff
        self.deck_id = mw.col.decks.by_name(deck_name)["id"]

    def _update_one(self, hunk):
        from_note = get_note_of_scope(self.from_source, hunk.source_start)
        to_note = get_note_of_scope(self.to_source, hunk.target_start)

        stripped_lines = get_stripped_lines(from_note)
        q = f"did:{self.deckid} hash:{hashlib.sha512(bytes("\n".join(stripped_lines), "utf-8")).hexdigest()}"
        note = mw.col.find_notes(q)[0]
        unote = mw.col.get_note(note)
        (recto, verso, hash) = CardGenerator(extend=True).gen_note_with_hash(to_note)
        unote.fields[0] = recto
        unote.fields[1] = verso
        unote.fields[2] = hash
        mw.col.update_note(unote)

    def _update_many(self, hunk):
        for i in hunk:
            pass

    def update(self):
        for hunk in self.diff:
            c = str(hunk).count("##")
            # FIXME: If ## don't start the hunk there is maybe other note
            if c == 1 or c == 0:
                self._update_one(hunk)
            else:
                self._update_many(hunk)


class DeleteFile:
    def __init__(self, from_source: str, deck_name: str):
        self.from_source = from_source
        self.deck_id = mw.col.decks.by_name(deck_name)["id"]

    def _delete_one(self, source: str):
        stripped_lines = get_stripped_lines(source)
        q = f"did:{self.deck_id} hash:{hashlib.sha512(bytes("\n".join(stripped_lines), "utf-8")).hexdigest()}"
        mw.col.remove_notes(mw.col.find_notes(q))

    def delete(self):
        for i in self.from_source.split("##"):
            self._delete_one("##" + i)


class Diff:
    def __init__(self, rev_from: str, rev_to: str):
        self.rev_from = rev_from
        self.rev_to = rev_to

    def update_deck_and_notes(self, mw):
        for i in PatchSet(Git().diff(self.rev_from, self.rev_to)):
            deck_name = i.path.split("/")[0]

            if i.is_added_file:
                continue

            if i.is_removed_file and not i.is_rename:
                from_source = Git().show(self.rev_from, i.path)
                DeleteFile(from_source, deck_name).delete()

            if i.is_modified_file:
                from_source = Git().show(self.rev_from, i.path)
                to_source = Git().show(self.rev_to, i.path)
                ModifiedFile(from_source, to_source, i, deck_name).update()
