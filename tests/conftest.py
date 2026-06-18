"""Shared test fixtures and configuration."""
import pytest


@pytest.fixture(scope="session")
def event_loop():
    """Need a session-scoped event loop for async tests."""
    import asyncio
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
