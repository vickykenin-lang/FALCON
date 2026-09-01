"""Stable exporter boundary for Falcon observability."""
from abc import ABC, abstractmethod

class TraceExporter(ABC):
    @abstractmethod
    def export(self,span)->None: ...
