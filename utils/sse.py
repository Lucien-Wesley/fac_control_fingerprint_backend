from __future__ import annotations

import json
import queue
import threading
from typing import Generator, Optional


class SSEBroker:
    """A minimal Server-Sent Events broker.

    Each subscriber receives events pushed after subscription time.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subscribers: list[queue.Queue[str]] = []

    def subscribe(self) -> queue.Queue[str]:
        q: queue.Queue[str] = queue.Queue(maxsize=100)
        with self._lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: queue.Queue[str]) -> None:
        with self._lock:
            try:
                self._subscribers.remove(q)
            except ValueError:
                pass

    def publish(self, event: str, data: dict) -> None:
        payload = f"event: {event}\n" f"data: {json.dumps(data)}\n\n"
        with self._lock:
            for q in list(self._subscribers):
                try:
                    q.put_nowait(payload)
                except queue.Full:
                    # Drop slow subscribers
                    self._subscribers.remove(q)

    def stream(self) -> Generator[str, None, None]:
        q = self.subscribe()
        try:
            # Initial ping to open stream on client
            yield "event: ping\ndata: {}\n\n"
            while True:
                msg = q.get()
                yield msg
        finally:
            self.unsubscribe(q)


sse_broker = SSEBroker()
