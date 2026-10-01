import uuid

import pytest
from fastapi import HTTPException

from app.services.rate_limit import check_rate_limit


def test_requests_within_the_limit_succeed():
    key = str(uuid.uuid4())
    for _ in range(5):
        check_rate_limit(key, max_requests=5, window_seconds=60)


def test_exceeding_the_limit_raises_429():
    key = str(uuid.uuid4())
    for _ in range(3):
        check_rate_limit(key, max_requests=3, window_seconds=60)
    with pytest.raises(HTTPException) as exc_info:
        check_rate_limit(key, max_requests=3, window_seconds=60)
    assert exc_info.value.status_code == 429


def test_different_keys_have_independent_limits():
    check_rate_limit(str(uuid.uuid4()), max_requests=1, window_seconds=60)
    check_rate_limit(str(uuid.uuid4()), max_requests=1, window_seconds=60)  # different key, fine
