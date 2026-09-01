"""Stable artifact backend boundary."""
from abc import ABC, abstractmethod

class ArtifactBackend(ABC):
    @abstractmethod
    def put(self,digest:str,data:bytes)->None: ...
    @abstractmethod
    def get(self,digest:str)->bytes: ...
