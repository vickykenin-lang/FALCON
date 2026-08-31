"""In-process Nervous System. Replaceable behind the same publish/subscribe contract."""
from collections import defaultdict
from typing import Callable
from contracts.models import Event

class EventBus:
    def __init__(self):
        self._subscribers: dict[str, list[Callable[[Event], None]]] = defaultdict(list)
        self.history: list[Event] = []

    def subscribe(self, event_type: str, handler: Callable[[Event], None]) -> None:
        self._subscribers[event_type].append(handler)

    def publish(self, event: Event) -> None:
        self.history.append(event)
        for handler in self._subscribers.get(event.event_type, []):
            handler(event)
        for handler in self._subscribers.get("*", []):
            handler(event)
