import pytest
from selection.selection import pick_rotation

POOL = ["hook-a", "hook-b", "hook-c"]

def test_avoids_most_recent():
    assert pick_rotation(POOL, recent=["hook-a"]) != "hook-a"

def test_picks_least_recently_used():
    # hook-a used longest ago, hook-c most recent -> expect hook-a
    assert pick_rotation(POOL, recent=["hook-a", "hook-b", "hook-c"]) == "hook-a"

def test_empty_recent_returns_first():
    assert pick_rotation(POOL, recent=[]) == "hook-a"

def test_single_item_pool_returns_it():
    assert pick_rotation(["only"], recent=["only"]) == "only"

def test_empty_pool_raises():
    with pytest.raises(ValueError, match="must not be empty"):
        pick_rotation([], recent=[])
