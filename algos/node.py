import random
import math
import simpy
import simpy.core
from typing import Dict, List
from abc import ABC, abstractmethod

from simpy.events import ProcessGenerator

class Node(ABC):
    id: int
    latency: float
    listening: bool

    @abstractmethod
    def run(self) -> ProcessGenerator:
        pass

    @property
    @abstractmethod
    def slotOffset(self) -> int:
        pass

    @property
    @abstractmethod
    def alignmentOffset(self) -> int:
        pass

    @property
    @abstractmethod
    def T(self) -> int:
        pass

    @property
    @abstractmethod
    def discoveredTimes(self) -> int:
        pass

    @property
    @abstractmethod
    def neighborsDiscovered(self) -> int:
        pass

    # @property
    # @abstractmethod
    # def isReceiving(self) -> bool:
    #     pass

    @abstractmethod
    def receiveMessage(self, msg: Dict) -> ProcessGenerator:
        pass


class NodeFactory(ABC):
    @abstractmethod
    def produce(self, env, mesgPipe: simpy.Store, slotOffset = 0, alignmentOffset = 0, id = 0, numNeighbors = 0) -> Node:
        pass

    @property
    @abstractmethod
    def nodeTypeName(self) -> str:
        pass
