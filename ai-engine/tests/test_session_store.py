"""Tests for ai_engine.core.session_store — async-safe in-memory store."""

from __future__ import annotations

import asyncio

import pytest
from ai_engine.core.session_store import SessionStore


@pytest.fixture()
def store():
    return SessionStore()


@pytest.mark.asyncio
async def test_create_and_get(store, make_session):
    session = make_session(call_id="c1")
    await store.create(session)
    result = await store.get("c1")
    assert result is session


@pytest.mark.asyncio
async def test_get_missing(store):
    result = await store.get("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_remove(store, make_session):
    session = make_session(call_id="c1")
    await store.create(session)
    removed = await store.remove("c1")
    assert removed is session
    assert await store.get("c1") is None


@pytest.mark.asyncio
async def test_remove_missing(store):
    result = await store.remove("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_list_active(store, make_session):
    await store.create(make_session(call_id="c1"))
    await store.create(make_session(call_id="c2"))
    active = await store.list_active()
    assert len(active) == 2
    ids = {s.call_id for s in active}
    assert ids == {"c1", "c2"}


@pytest.mark.asyncio
async def test_count(store, make_session):
    assert await store.count() == 0
    await store.create(make_session(call_id="c1"))
    assert await store.count() == 1
    await store.create(make_session(call_id="c2"))
    assert await store.count() == 2
    await store.remove("c1")
    assert await store.count() == 1


@pytest.mark.asyncio
async def test_concurrent_creates(store, make_session):
    """Multiple concurrent creates should not lose data."""
    sessions = [make_session(call_id=f"c{i}") for i in range(20)]
    await asyncio.gather(*(store.create(s) for s in sessions))
    assert await store.count() == 20


@pytest.mark.asyncio
async def test_overwrite(store, make_session):
    """Creating a session with same call_id overwrites the previous one."""
    s1 = make_session(call_id="c1", caller_name="Alice")
    s2 = make_session(call_id="c1", caller_name="Bob")
    await store.create(s1)
    await store.create(s2)
    result = await store.get("c1")
    assert result.caller_name == "Bob"
