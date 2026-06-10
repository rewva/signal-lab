"""The default runtime should register all three platform adapters."""

from publisher.bootstrap import _default_adapters
from publisher.config import Settings


def test_default_adapters_cover_all_three_platforms():
    adapters = _default_adapters(Settings())
    assert set(adapters) == {"youtube", "facebook", "instagram"}


def test_each_adapter_reports_matching_platform():
    adapters = _default_adapters(Settings())
    for platform, adapter in adapters.items():
        assert adapter.platform == platform
