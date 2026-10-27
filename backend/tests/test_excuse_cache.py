import asyncio
from app import llm, excuses


def test_partial_reply_not_cached(monkeypatch):
    async def crashing_streamer(*args, **kwargs):
        yield "Wachira has built a FastAPI backend that stre"
        raise llm.LLMError("connection dropped")

    monkeypatch.setitem(llm.STREAMERS, "groq", crashing_streamer)
    monkeypatch.setattr(llm, "configured_providers", lambda: ["groq"])
    excuses._cache.clear()

    async def run():
        return [f async for f in llm.stream_excuse_buster(1, 123.0)]

    asyncio.run(run())
    assert excuses.get_cached_excuse(1, 123.0) is None
