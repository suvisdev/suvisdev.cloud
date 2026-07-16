from __future__ import annotations

from abc import ABC, abstractmethod

from ontology.domain.events.spoke_events import CrawlCompletedEvent


class CrawlEventPublisherPort(ABC):
    @abstractmethod
    def publish(self, event: CrawlCompletedEvent) -> None: ...
