from __future__ import annotations

from dataclasses import dataclass

from selection.selection import template_for, POSITIONS


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


@dataclass
class RenderPlan:
    """The subset of DayPlan frozen at planning time and needed for assembly.
    A real DayPlan is structurally compatible (same attribute names)."""
    answer_position: str
    cta: str
    trick_hook: str = ""


def _category_label(domain: str, labels: dict) -> str:
    if domain in labels:
        return labels[domain]
    return domain.replace("-", " ").title()  # fallback: "general-science" -> "General Science"


def quiz_props(question, plan, day_number: int, labels: dict) -> dict:
    """Map a verified Question + frozen plan fields into the renderer's QuizProps dict."""
    return {
        "dayNumber": day_number,
        "category": _category_label(question.domain, labels),
        "difficulty": question.difficulty,
        "examPrefix": question.exam_relevance[0] if question.exam_relevance else "",
        "template": template_for(question.is_trick),
        "question": question.question,
        "options": order_options(question.answer, question.distractors, plan.answer_position),
        "correctLetter": plan.answer_position,
        "explanation": question.explanation,
        "sourceLine": question.source_citation,
        "cta": plan.cta,
        "trickHook": plan.trick_hook,
    }


DEFAULT_PLATFORMS = ("youtube", "facebook", "instagram")
DEFAULT_CHANNEL_ID = "daily-gk-quiz"


def _hashtag(text: str) -> str:
    """A compact alphanumeric hashtag: 'IBPS-SBI' -> '#IBPSSBI'."""
    cleaned = "".join(ch for ch in text if ch.isalnum())
    return "#" + cleaned


def job_submission(question, day_number: int, video_path: str, description: str,
                   ai_disclosure: bool, labels: dict,
                   channel_id: str = DEFAULT_CHANNEL_ID,
                   platforms: list[str] | None = None) -> dict:
    """Build the POST /api/jobs body for one verified, rendered question."""
    category = _category_label(question.domain, labels)
    tags = [_hashtag(e) for e in question.exam_relevance]
    tags += [_hashtag(category), "#PakkaGK", "#GKQuiz"]
    full_description = f"{description}\n\nSource: {question.source_citation}"
    return {
        "channel_id": channel_id,
        "video_path": video_path,
        "title": f"Pakka GK #{day_number} - {category}",
        "description": full_description,
        "tags": tags,
        "platforms": list(platforms) if platforms is not None else list(DEFAULT_PLATFORMS),
        "per_platform": {"youtube": {"ai_disclosure": ai_disclosure}},
        "source_citation": question.source_citation,
        "sources": list(question.sources),
    }
