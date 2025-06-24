import asyncio

class Broadcaster:
    """단일 프로세스용 간단 pub/sub (필요 시 Redis로 대체)."""
    def __init__(self):
        self.subscribers: list[asyncio.Queue] = []

    async def publish(self, msg: dict):
        for q in self.subscribers:
            await q.put(msg)

    async def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self.subscribers.append(q)
        return q

broadcaster = Broadcaster()