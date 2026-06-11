from __future__ import annotations

POSITIONS = ("A", "B", "C", "D")


def order_options(answer: str, distractors: list[str], position: str) -> list[dict]:
    """The 4 A/B/C/D options with `answer` in `position` and the 3 distractors
    filling the remaining slots in order. Deterministic."""
    if len(distractors) != 3:
        raise ValueError("order_options needs exactly 3 distractors")
    if position not in POSITIONS:
        raise ValueError(f"position must be one of {POSITIONS}")
    remaining = list(distractors)
    options = []
    for letter in POSITIONS:
        text = answer if letter == position else remaining.pop(0)
        options.append({"letter": letter, "text": text})
    return options
