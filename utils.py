def get_stripped_lines(s: str) -> [str]:
    return [line.strip() for line in s.splitlines() if len(line.strip()) != 0]


def is_extends(s: str):
    return any([i.startswith("%") for i in get_stripped_lines(s)])
