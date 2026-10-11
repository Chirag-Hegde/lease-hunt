from app.services.redact import redact_payload, redact_pii


def test_redact_pii() -> None:
    text = "Contact John at john.doe@example.com or (408) 555-1234, SSN 123-45-6789."
    redacted = redact_pii(text)
    assert "john.doe" not in redacted
    assert "555-1234" not in redacted
    assert "123-45-6789" not in redacted
    assert "[email]" in redacted and "[phone]" in redacted and "[ssn]" in redacted


def test_redact_payload_recursive() -> None:
    payload = {"a": ["email me@x.io"], "b": {"c": "call 650-555-0000"}, "n": 3}
    out = redact_payload(payload)
    assert out["a"][0] == "email [email]"
    assert out["b"]["c"] == "call [phone]"
    assert out["n"] == 3


def test_rate_limiter_blocks_after_limit() -> None:
    from app.services.ratelimit import SlidingWindowLimiter

    limiter = SlidingWindowLimiter(limit_per_minute=5)
    results = [limiter.check("client")[0] for _ in range(6)]
    assert results[:5] == [True] * 5
    assert results[5] is False


async def test_circuit_breaker_opens_and_recovers() -> None:
    import httpx

    from app.services.resilience import CircuitBreaker, CircuitOpenError

    breaker = CircuitBreaker("test-api", threshold=3, cooldown_s=0.05)
    calls = 0

    async def failing() -> str:
        nonlocal calls
        calls += 1
        raise httpx.ConnectError("boom")

    import pytest

    for _ in range(2):
        with pytest.raises((httpx.ConnectError, CircuitOpenError)):
            await breaker.call(failing, retries=1, base_delay_s=0.001)
    with pytest.raises(CircuitOpenError):
        await breaker.call(failing, retries=0)

    # After cooldown, a succeeding probe closes the circuit.
    import asyncio

    await asyncio.sleep(0.06)

    async def ok() -> str:
        return "fine"

    assert await breaker.call(ok) == "fine"
