import subprocess


class Git:
    def __init__(self):
        self.cmd = "/usr/bin/git"

    def exe(self, *args: str):
        return subprocess.run([self.cmd] + list(args), capture_output=True)

    def clone(self, url: str, to: str):
        self.exe("clone", url, to)

    def pull(self) -> str:
        return self.exe("pull").stdout.decode("utf-8")

    def show(self, rev: str, file: str) -> str:
        return self.exe("--no-pager", "show", f"{rev}:{file}").stdout.decode("utf-8")

    def diff(self, from_rev: str, to_rev: str) -> str:
        return self.exe("--no-pager", "diff", f"{from_rev}..{to_rev}").stdout.decode(
            "utf-8"
        )
