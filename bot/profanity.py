from __future__ import annotations

import re

_ROOTS = [
    r"бл[яa][тдь]",
    r"су[кk][аоиeу]",
    r"п[иi]зд",
    r"еб[ао]",
    r"еб[уы]",
    r"е[бb]ан",
    r"хуй",
    r"хуя",
    r"ху[ёe]в",
    r"п[ао]ху[йия]",
    r"нах[уy][йия]",
    r"уеб",
    r"мудак",
    r"гнид",
    r"чмо",
    r"f+u+c+k",
    r"sh+i+t",
    r"b+i+t+c+h",
    r"a+s+s+h+o+l+e",
    r"c+u+n+t",
]

_PATTERN = re.compile(r"(?ui)\b(" + "|".join(_ROOTS) + r")\w*\b")


def is_profane(text: str) -> bool:
    return bool(text and _PATTERN.search(text))
