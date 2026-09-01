"""Stable persistence boundary for Falcon Memory."""
from abc import ABC,abstractmethod
class MemoryBackend(ABC):
    @abstractmethod
    def append(self,item:dict)->None: ...
    @abstractmethod
    def recent(self,limit:int)->list[dict]: ...
