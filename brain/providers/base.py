"""Replaceable intelligence provider contract."""
from abc import ABC, abstractmethod
class IntelligenceProvider(ABC):
    @abstractmethod
    def decide(self, objective: str, context: dict) -> dict:
        """Return structured decision: summary, actions, success_criteria."""
        raise NotImplementedError
