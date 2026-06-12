from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional

DIFFICULTIES = ("basic", "intermediate", "advanced")
EXAMS = ("SSC", "IBPS-SBI", "RRB")

@dataclass
class Question:
    domain: str
    difficulty: str
    fact_key: str
    entity: str
    question: str
    answer: str
    distractors: list[str]
    exam_relevance: list[str]
    sources: list[str]
    explanation: str = ""          # trailing defaults keep positional construction valid
    mnemonic: Optional[str] = None
    is_trick: bool = False
    source_citation: str = ""      # human-readable on-screen citation (distinct from sources URLs)

    def validate(self) -> "Question":
        if self.difficulty not in DIFFICULTIES:
            raise ValueError(f"difficulty must be one of {DIFFICULTIES}")
        if len(self.distractors) != 3:
            raise ValueError("a question needs exactly 3 distractors")
        if len(self.sources) < 2:
            raise ValueError("a question needs at least 2 sources")
        if not self.explanation.strip():
            raise ValueError("explanation is required (per-video pedagogy)")
        if not self.source_citation.strip():
            raise ValueError("source_citation is required (on-screen citation / trust badge)")
        bad = [e for e in self.exam_relevance if e not in EXAMS]
        if bad:
            raise ValueError(f"unknown exam_relevance {bad}; allowed {EXAMS}")
        return self

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Question":
        return cls(
            domain=d["domain"], difficulty=d["difficulty"], fact_key=d["fact_key"],
            entity=d["entity"], question=d["question"], answer=d["answer"],
            distractors=list(d["distractors"]), exam_relevance=list(d["exam_relevance"]),
            sources=list(d["sources"]),
            explanation=d.get("explanation", ""), mnemonic=d.get("mnemonic"),
            is_trick=d.get("is_trick", False),
            source_citation=d.get("source_citation", ""),
        )

STATIC_CLASSES = ("permanent", "slowly-changing")
STATUSES = ("draft", "verified", "retired")
YIELD_WEIGHTS = {"high": 3, "medium": 2, "low": 1}


@dataclass
class BankEntry:
    question: Question
    static_class: str          # one of STATIC_CLASSES
    source_tier: int           # 1 | 2 | 3
    yield_weight: str          # key of YIELD_WEIGHTS
    status: str = "draft"      # one of STATUSES
    verified_date: Optional[str] = None    # ISO date; set when verified
    review_due_date: Optional[str] = None  # ISO date; None for permanent

    def to_dict(self) -> dict:
        return {
            "question": self.question.to_dict(),
            "static_class": self.static_class,
            "source_tier": self.source_tier,
            "yield_weight": self.yield_weight,
            "status": self.status,
            "verified_date": self.verified_date,
            "review_due_date": self.review_due_date,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "BankEntry":
        return cls(
            question=Question.from_dict(d["question"]),
            static_class=d["static_class"],
            source_tier=d["source_tier"],
            yield_weight=d["yield_weight"],
            status=d.get("status", "draft"),
            verified_date=d.get("verified_date"),
            review_due_date=d.get("review_due_date"),
        )


@dataclass
class HistoryRecord:
    date: str
    question: Question
    hook: Optional[str] = None
    cta: Optional[str] = None
    answer_position: Optional[str] = None
    trick_hook: Optional[str] = None

    def to_dict(self) -> dict:
        return {"date": self.date, "hook": self.hook, "cta": self.cta,
                "answer_position": self.answer_position, "trick_hook": self.trick_hook,
                **self.question.to_dict()}

    @classmethod
    def from_dict(cls, d: dict) -> "HistoryRecord":
        return cls(date=d["date"], question=Question.from_dict(d),
                   hook=d.get("hook"), cta=d.get("cta"),
                   answer_position=d.get("answer_position"),
                   trick_hook=d.get("trick_hook"))
