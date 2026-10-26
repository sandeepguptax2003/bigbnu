import asyncio
from dataclasses import replace
from datetime import datetime, timezone

import pytest

from app.config import settings
from app.domain import Forecast
from app.elexon import UpstreamError
from app.service import DataStore

T = datetime(2026, 1, 5, 10, tzinfo=timezone.utc)


class FakeClient:
    def __init__(self):
        self.calls = 0
        self.fail = False

    async def load(self, start, end):
        self.calls += 1
        await asyncio.sleep(0.01)
        if self.fail:
            raise UpstreamError("down")
        return {T: 1000.0}, [Forecast(T, T.replace(hour=4), 900.0)]


def test_concurrent_cold_requests_share_one_refresh():
    client = FakeClient()
    store = DataStore(settings, client)

    async def run():
        return await asyncio.gather(*(store.snapshot() for _ in range(20)))

    snapshots = asyncio.run(run())
    assert client.calls == 1
    assert all(s is snapshots[0] for s in snapshots)


def test_expired_snapshot_is_served_while_refreshing_in_background():
    client = FakeClient()
    store = DataStore(replace(settings, cache_ttl_seconds=0), client)

    async def run():
        first = await store.snapshot()
        stale = await store.snapshot()
        again = await store.snapshot()
        await store._refresh_task
        fresh = await store.snapshot()
        return first, stale, again, fresh

    first, stale, again, fresh = asyncio.run(run())
    assert stale is first and again is first
    assert fresh is not first
    assert client.calls >= 2


def test_background_failure_keeps_serving_stale_snapshot():
    client = FakeClient()
    store = DataStore(replace(settings, cache_ttl_seconds=0, stale_retry_seconds=60), client)

    async def run():
        first = await store.snapshot()
        client.fail = True
        await store.snapshot()
        await store._refresh_task
        return first, await store.snapshot()

    first, later = asyncio.run(run())
    assert later is first
    assert client.calls == 2


def test_cold_failure_is_negatively_cached():
    client = FakeClient()
    client.fail = True
    store = DataStore(settings, client)

    async def run():
        for _ in range(3):
            with pytest.raises(UpstreamError):
                await store.snapshot()

    asyncio.run(run())
    assert client.calls == 1


def test_store_survives_a_new_event_loop():
    client = FakeClient()
    store = DataStore(replace(settings, cache_ttl_seconds=0), client)
    asyncio.run(store.snapshot())
    asyncio.run(store.snapshot())
    assert client.calls >= 1
