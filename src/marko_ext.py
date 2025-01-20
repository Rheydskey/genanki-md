import marko
import re
from typing import TYPE_CHECKING, Match, NamedTuple, Union


class EmbedLatex(marko.inline.InlineElement):
    priority = 5
    pattern = re.compile(r"(\$\$.+\$\$)")
    parse_children = True

    def __init__(self, match: tuple[str]) -> None:
        self.source = match[0]


class EmbedLatexMixin(object):
    def render_embed_latex(self, element):
        return '{}'.format(element.source)
