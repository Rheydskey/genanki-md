"""
Migration of mdanki card to ankill card

"""

import re
import html


class MdAnkiMigrator:
    def __init__(self):
        pass

    def convert(self, s: str) -> str:
        lines = s.splitlines()
        convert_lines = []

        for line in lines:
            if "id=" in line:
                line = re.sub(' ?id="[a-zÀ-ÿ0-9-]+"', "", line, flags=re.IGNORECASE)
            if "<br>" in line:
                line = re.sub("<br>", "\n", line, flags=re.IGNORECASE)
            if "\\" in line:
                # Love escaping
                line = re.sub("\\\\\\\\", "\\\\", line)
            line = html.unescape(line)
            convert_lines.append(line.strip())

        return "\n".join(convert_lines)
