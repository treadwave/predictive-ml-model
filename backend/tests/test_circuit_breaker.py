from app.core.circuit_breaker import CircuitBreaker


def fail(breaker: CircuitBreaker, times: int) -> None:
    for _ in range(times):
        breaker.check_half_open()
        breaker.errors_counter()


def test_stays_closed_below_threshold():
    breaker = CircuitBreaker(error_threesold=3, time=60)

    fail(breaker, 2)

    assert breaker.allow_request()


def test_blocks_requests_after_threshold():
    breaker = CircuitBreaker(error_threesold=3, time=60)

    fail(breaker, 3)

    assert not breaker.allow_request()


def test_allows_probe_after_timeout():
    breaker = CircuitBreaker(error_threesold=3, time=0)

    fail(breaker, 3)

    assert breaker.allow_request()
    assert breaker.state == "half-open"


def test_failed_probe_reopens():
    breaker = CircuitBreaker(error_threesold=3, time=60)
    fail(breaker, 3)
    breaker.half_open()

    breaker.check_half_open()

    assert breaker.state == "open"
    assert not breaker.allow_request()


def test_success_closes():
    breaker = CircuitBreaker(error_threesold=3, time=60)
    fail(breaker, 3)

    breaker.set_closed()

    assert breaker.allow_request()
    assert breaker.errors == 0
