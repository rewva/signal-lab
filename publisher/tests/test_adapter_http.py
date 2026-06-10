"""Tests for the shared adapter HTTP status classifier."""

import pytest

from publisher.adapters.errors import FatalError, RetryableError
from publisher.adapters.http import classify_status


@pytest.mark.parametrize("status", [429, 500, 502, 503])
def test_transient_statuses_are_retryable(status):
    with pytest.raises(RetryableError):
        classify_status(status)


@pytest.mark.parametrize("status", [400, 401, 403, 404])
def test_client_errors_are_fatal(status):
    with pytest.raises(FatalError):
        classify_status(status)


@pytest.mark.parametrize("status", [200, 201, 204])
def test_success_does_not_raise(status):
    assert classify_status(status) is None
