def get_stripped_lines(s: str) -> [str]:
    return [line.strip() for line in s.splitlines()]


def is_extends(s: str):
    return any([i.startswith("%") for i in get_stripped_lines(s)])
