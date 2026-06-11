import pytest
from selection.assemble import order_options


def test_answer_placed_in_each_position():
    answer = "Article 21"
    distractors = ["Article 19", "Article 14", "Article 32"]
    for pos in ("A", "B", "C", "D"):
        opts = order_options(answer, distractors, pos)
        assert [o["letter"] for o in opts] == ["A", "B", "C", "D"]
        by_letter = {o["letter"]: o["text"] for o in opts}
        assert by_letter[pos] == answer
        # the three distractors fill the other slots, in order
        others = [o["text"] for o in opts if o["letter"] != pos]
        assert others == distractors


def test_position_c_layout():
    opts = order_options("ANS", ["d0", "d1", "d2"], "C")
    assert opts == [
        {"letter": "A", "text": "d0"},
        {"letter": "B", "text": "d1"},
        {"letter": "C", "text": "ANS"},
        {"letter": "D", "text": "d2"},
    ]


def test_rejects_wrong_distractor_count():
    with pytest.raises(ValueError):
        order_options("ANS", ["only", "two"], "A")
