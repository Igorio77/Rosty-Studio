"""A minimal synchronous in-process pub/sub bus (CLAUDE.md mentions an
"event bus" under services/). Deliberately tiny for now — this exists so UI
panels can react to data changes (e.g. "assignment added") without a direct
import cycle back into the panel that made the change, not to be a general
messaging framework.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from typing import Any


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable[[Any], None]]] = defaultdict(list)

    def subscribe(self, event_name: str, handler: Callable[[Any], None]) -> None:
        self._subscribers[event_name].append(handler)

    def unsubscribe(self, event_name: str, handler: Callable[[Any], None]) -> None:
        if handler in self._subscribers[event_name]:
            self._subscribers[event_name].remove(handler)

    def publish(self, event_name: str, payload: Any = None) -> None:
        for handler in list(self._subscribers.get(event_name, [])):
            handler(payload)
