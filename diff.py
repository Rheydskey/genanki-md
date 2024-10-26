import unidiff

class DiffObject:
    def __init__(self, prev, next):
        self.prev = prev
        self.next = next

    # def from_file(path: pathlib.Path) -> DiffObject:
    #     pass

class Diff:
    def __init__(self, rev_from: str, rev_to: str):
        self.rev_from = rev_from
        self.rev_to = rev_to

    def update_notes(self):
        print(self.rev_from)
