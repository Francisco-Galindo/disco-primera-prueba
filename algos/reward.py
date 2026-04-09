import math
import random
import simpy
import simpy.core
import queue
import numpy as np
from simpy.util import start_delayed
from algos.node import Node, NodeFactory
from typing import Dict, TypedDict, Set, List
from operator import add


class Discovery(TypedDict):
    id: int
    time: str


class RewardNodeFactory(NodeFactory):
    def __init__(self, startDC=0.05, alpha=0.0546875) -> None:
        self.startDC = startDC
        self.alpha = alpha

    def produce(self, env, mesgPipe: simpy.Store, slotOffset=0, alignmentOffset=0, id=0, numNeighbors=0) -> Node:
        return RewardNode(env, mesgPipe, slotOffset, self.startDC, alignmentOffset, self.alpha, id, numNeighbors)

    @property
    def nodeTypeName(self) -> str:
        return "Reward 1"


class RewardNode(Node):
    def __init__(self, env, mesgPipe: simpy.Store, slotOffset=0, dutycycle=0.05, alignmentOffset=0, alpha=0.0546875, id=0, numNeighbors=0) -> None:
        self.id = id
        self._alpha = alpha
        self._m = math.ceil(2 / dutycycle)
        self._n = math.ceil(alpha / dutycycle)
        self.listening = False
        self.transmitting = False
        self.env = env
        self.inPipeCount = 0
        self.inPipe = queue.Queue()
        self.outPipe = mesgPipe
        self.latency = 10_000_000_000_000_000
        self.collisions = 0
        self.cleanDiscoveries = 0
        self.numNeighbors = numNeighbors
        self.lastListenSartTime = 0
        self.DCUpdates = []
        self.finalDC = 0

        self._turnedOn = False
        self._slotOffset = slotOffset
        self._alignmentOffset = alignmentOffset
        self._cycleJustStarted = False
        self._startingTime = 0
        self._receivingMessage = False
        self._shouldStop = False

        self.setDutyCycle(dutycycle)

        self._DC = dutycycle
        self._activeSlots = 0

        self._newDiscoveriesMem = []
        self._collisionMem = []
        self._cleanDiscoveryMem = []
        self._totalDiscoveries = []

        self._discovered: Set[int] = set()
        self._discoveredTimes: List[int] = []
        self._collisionTimes: List[int] = []
        self._simStartTime = 0

        if not slotOffset:
            self.restart()

    def setSimStartTime(self, time):
        self._simStartTime = time

    def setDutyCycle(self, dutycycle=0.05) -> None:
        # self._m = math.ceil(2 / dutycycle)
        # self._n = math.ceil(self._alpha / dutycycle)
        pass

    def getDutyCycle(self) -> float:
        return 2 / self._m

    def stop(self):
        self._shouldStop = True

    @property
    def n(self) -> int:
        return self._n

    @property
    def m(self) -> int:
        return self._m

    @property
    def discoveredTimes(self) -> int:
        return self._discoveredTimes

    @property
    def collisionTimes(self) -> int:
        return self._collisionTimes

    @property
    def alpha(self) -> int:
        return self._alpha

    @property
    def slotOffset(self) -> int:
        return self._slotOffset

    @property
    def alignmentOffset(self) -> int:
        return self._alignmentOffset

    @property
    def T(self) -> int:
        return 100

    @property
    def neighborsDiscovered(self) -> int:
        return len(self._discovered)

    def restart(self) -> None:
        self._discovered: Set[int] = set()
        self.listening = False

        # print(f'alpha: {self.alpha}')
        self._alignmentOffset = 0
        self._slotOffset = 0

        self.latency = 1_000_000_000_000_000

        if self.id != 0 and self.numNeighbors > 0:
            self._alignmentOffset = random.uniform(0, 1)
            self._slotOffset = random.randint(0, self.T-1)

        self._startingTime = self._alignmentOffset + self._slotOffset
        # print('slot\t', self._slotOffset)

    def receiveMessage(self, msg: Dict):

        cleanStart = True
        if not self.inPipe.empty():
            cleanStart = False

        sender = msg["from"]
        self.inPipe.put(sender)

        listeningFromTheStart = self.listening

        yield self.env.timeout(msg["alpha"])

        # if self.env.now - self.lastListenSartTime > 1 - self.alpha:
        #     return

        # Remove this new element after listening time is over
        sender_after = self.inPipe.get()

        cleanEnd = True
        if not self.inPipe.empty():
            cleanEnd = False

        if not listeningFromTheStart:
            return

        cleanDiscovery = cleanEnd and cleanStart
        newDiscovery = cleanDiscovery and sender not in self._discovered
        if newDiscovery:
            now = self.env.now

            self._discovered.add(msg["from"])
            # self._discoveredTimes.append(math.ceil(now))

            if self.latency > 1_000_000_000 and self.hasDiscoveredAllNeighbors():
                self.latency = math.ceil(self.env.now)
                # if self.id == 0:
                #     # print(f'latency\t{self.latency}, asdfasdf {self.slotOffset}')
                #     print(f'lat\t{self.latency}\t{self.numNeighbors}')
                # self.finalDC = self._activeSlots / self.latency
                self.finalDC = self._DC
                # print("YA TERMINÉ", self.latency)
                # print(self.finalDC, self._DC) # !!!
                # print("DC", self._activeSlots / self.latency)

        elif cleanDiscovery:
            self.cleanDiscoveries += 1
        elif not cleanDiscovery:
            # print("collision", self.env.now)
            self.collisions += 1
            # self._collisionTimes.append(math.ceil(self.env.now))

    def hasdiscoveredallneighbors(self):
        return self.numneighbors == len(self._discovered)

    def doTX(self):
        now = self.env.now
        timeToListen = 100000000000
        msg = {
            "now": now,
            "timeToListen": timeToListen,
            "alpha": self._alpha,
            "from": self.id
        }

        self.listening = False
        self.transmitting = True
        self.outPipe.put(msg)
        yield self.env.timeout(self._alpha)
        self.transmitting = False

    def updateDutyCycle(self):
        Ncurr = len(self._discovered) + 1
        eta = 10.0
        T = 100

        DC = self._DC * 100

        term1 = 2 / DC
        term2 = (4*self.alpha*(Ncurr - 2)) / (T - 4*self.alpha*DC)
        gradient = term1 - term2
        step = eta * 99 * np.tanh(gradient)

        newDC = float(DC + step)

        self._DC = np.clip(newDC/100, 0.01, 0.99)

    def genDifferenceList(self, lst):
        return [lst[i+1] - lst[i] for i in range(len(lst)-1)]

    def doCycleStart(self):
        if self._shouldStop:
            return
        # print(f"{self.env.now}: \t{self.id} starts FIRST LISTENING")
        self.lastListenSartTime = self.env.now
        self._cycleJustStarted = True

        if self.env.now > self._simStartTime:
            self.updateDutyCycle()
            self.DCUpdates.append((round(self.env.now), self._DC))

        # self._DC = max(0.01, self._DC)
        # self._DC = min(0.15, self._DC)
        self._activeSlots += self._DC * 100

        beaconTimes = []
        while len(beaconTimes) < round(self._DC / 0.01):
            beaconTime = random.random() * 99
            isNew = True
            for time in beaconTimes:
                if 0 <= beaconTime - time <= 1:
                    isNew = False
                    break

            if isNew:
                beaconTimes.append(beaconTime)

        for beaconTime in beaconTimes:
            if beaconTime == 0:
                self.env.process(self.activeSlotSequence())
            else:
                start_delayed(self.env, self.activeSlotSequence(), beaconTime)
        # Won't run without it
        yield self.env.timeout(1)
        return

    def activeSlotSequence(self):
        # if self.listening or self.transmitting:
        #     yield self.env.timeout(self.alpha)
        #     self._activeSlots -= 1
        #     print("PAPEADO")
        #     return
        # if self.id == 0:
        #     print('TX', self.env.now)
        self.env.process(self.doTX())
        yield self.env.timeout(self.alpha)
        # if self.id == 0:
        #     print('LISTENING', self.env.now)
        # print('alpha', self.alpha, self._alpha)
        self.env.process(self.doListen()) # Also does the second TX

    def doListen(self):
        # print(f"{self.env.now}: \t{self.id} starts NORMAL LISTENING")
        self._cycleJustStarted = False
        self.lastListenSartTime = self.env.now
        # self.inPipeCount = 0
        self.listening = True
        yield self.env.timeout(1 - 2 * self.alpha)

        # self.inPipe = []
        self.inPipeCount = 0
        self.listening = False
        yield self.env.process(self.doTX())
        # print(f"{self.env.now}: \t{self.id} stops LISTENING")

    def run(self, maxtime: int):
        yield self.env.timeout(self._startingTime)
        # print(f"Current Heap Size: {len(self.env._queue)}")

        while self.env.now < maxtime and not self._shouldStop:
            self.env.process(self.doCycleStart())
            yield self.env.timeout(100)

        self._discoveredTimes.sort()
        self._collisionTimes.sort()
        self.DCUpdates.sort()


class Reward2NodeFactory(NodeFactory):
    def __init__(self, startDC=0.05, alpha=0.0546875) -> None:
        self.startDC = startDC
        self.alpha = alpha

    def produce(self, env, mesgPipe: simpy.Store, slotOffset=0, alignmentOffset=0, id=0, numNeighbors=0) -> Node:
        return Reward2Node(env, mesgPipe, slotOffset, self.startDC, alignmentOffset, self.alpha, id, numNeighbors)

    @property
    def nodeTypeName(self) -> str:
        return "Reward 2"


class Reward2Node(RewardNode):
    def __init__(self, env, mesgPipe: simpy.Store, slotOffset=0, dutycycle=0.05, alignmentOffset=0, alpha=0.0546875, id=0, numNeighbors=0) -> None:
        self.id = id
        self._alpha = alpha
        self._m = math.ceil(2 / dutycycle)
        self._n = math.ceil(alpha / dutycycle)
        self.listening = False
        self.transmitting = False
        self.env = env
        self.inPipe = queue.Queue()
        self.outPipe = mesgPipe
        self.latency = 10_000_000_000
        self.collisions = 0
        self.cleanDiscoveries = 0
        self.numNeighbors = numNeighbors
        self.lastListenSartTime = 0
        self.DCUpdates = []
        self.finalDC = 0

        self._turnedOn = False
        self._slotOffset = slotOffset
        self._alignmentOffset = alignmentOffset
        self._cycleJustStarted = False
        self._startingTime = 0
        self._receivingMessage = False
        self._shouldStop = False

        self.setDutyCycle(dutycycle)

        self._DC = dutycycle
        self._activeSlots = 0

        self._newDiscoveriesMem = []
        self._collisionMem = []
        self._cleanDiscoveryMem = []
        self._totalDiscoveries = []

        self._discovered: Set[int] = set()
        self._discoveredTimes: List[int] = []
        self._collisionTimes: List[int] = []
        self._simStartTime = 0

        if not slotOffset:
            self.restart()

    def updateDutyCycle(self):
        if len(self._totalDiscoveries) < 4:
            self._newDiscoveriesMem.append(len(self._discovered))

            if len(self._newDiscoveriesMem) <= 2:
                if self._newDiscoveriesMem[-1] == 0:
                    self._DC += 0.02
            elif len(self._newDiscoveriesMem) > 2:
                perfDiff = self.genDifferenceList(self._newDiscoveriesMem)
                if perfDiff[-1] == 0:
                    self._DC += 0.01 * len(self._newDiscoveriesMem)

        else:
            self._newDiscoveriesMem = self._perfList[1:]
            self._newDiscoveriesMem.append(len(self._discovered))

            perfDiff = self.genDifferenceList(self._newDiscoveriesMem)
            perf2Diff = self.genDifferenceList(perfDiff)

            if perf2Diff[1] <= 0.9 * perf2Diff[0]:
                self._DC += 0.04
            elif perf2Diff[1] >= 1.1 * perf2Diff[0]:
                self._DC -= 0.01


class Reward3NodeFactory(NodeFactory):
    def __init__(self, startDC=0.05, alpha=0.0546875) -> None:
        self.startDC = startDC
        self.alpha = alpha

    def produce(self, env, mesgPipe: simpy.Store, slotOffset=0, alignmentOffset=0, id=0, numNeighbors=0) -> Node:
        return Reward3Node(env, mesgPipe, slotOffset, self.startDC, alignmentOffset, self.alpha, id, numNeighbors)

    @property
    def nodeTypeName(self) -> str:
        return "Reward 3"


class Reward3Node(RewardNode):
    def __init__(self, env, mesgPipe: simpy.Store, slotOffset=0, dutycycle=0.05, alignmentOffset=0, alpha=0.0546875, id=0, numNeighbors=0) -> None:
        self.id = id
        self._alpha = alpha
        self._m = math.ceil(2 / dutycycle)
        self._n = math.ceil(alpha / dutycycle)
        self.listening = False
        self.transmitting = False
        self.env = env
        self.inPipe = queue.Queue()
        self.outPipe = mesgPipe
        self.latency = 10_000_000_000
        self.collisions = 0
        self.cleanDiscoveries = 0
        self.numNeighbors = numNeighbors
        self.lastListenSartTime = 0
        self.DCUpdates = []
        self.finalDC = 0

        self._turnedOn = False
        self._slotOffset = slotOffset
        self._alignmentOffset = alignmentOffset
        self._cycleJustStarted = False
        self._startingTime = 0
        self._receivingMessage = False
        self._shouldStop = False

        self.setDutyCycle(dutycycle)

        self._DC = dutycycle
        self._activeSlots = 0

        self._newDiscoveriesMem = []
        self._collisionMem = []
        self._cleanDiscoveryMem = []
        self._totalDiscoveries = []

        self._discovered: Set[int] = set()
        self._discoveredTimes: List[int] = []
        self._collisionTimes: List[int] = []
        self._simStartTime = 0

        if not slotOffset:
            self.restart()

    def updateDutyCycle(self):
        self._cleanDiscoveryMem.append(self.cleanDiscoveries)
        if len(self._cleanDiscoveryMem) > 3:
            self._cleanDiscoveryMem = self._cleanDiscoveryMem[1:]

            if self._cleanDiscoveryMem[-1] == self._cleanDiscoveryMem[-2]:
                self._DC += 0.1
            elif len(self._cleanDiscoveryMem) >= 3 and self._cleanDiscoveryMem[-3] < self._cleanDiscoveryMem[-2] and self._cleanDiscoveryMem[-2] < self._cleanDiscoveryMem[-1]:
                self._DC -= 0.1


class Reward4NodeFactory(NodeFactory):
    def __init__(self, startDC=0.05, alpha=0.0546875) -> None:
        self.startDC = startDC
        self.alpha = alpha

    def produce(self, env, mesgPipe: simpy.Store, slotOffset=0, alignmentOffset=0, id=0, numNeighbors=0) -> Node:
        return Reward4Node(env, mesgPipe, slotOffset, self.startDC, alignmentOffset, self.alpha, id, numNeighbors)

    @property
    def nodeTypeName(self) -> str:
        return "Reward 4"


class Reward4Node(RewardNode):
    def __init__(self, env, mesgPipe: simpy.Store, slotOffset=0, dutycycle=0.05, alignmentOffset=0, alpha=0.0546875, id=0, numNeighbors=0) -> None:
        self.id = id
        self._alpha = alpha
        self._m = math.ceil(2 / dutycycle)
        self._n = math.ceil(alpha / dutycycle)
        self.listening = False
        self.transmitting = False
        self.env = env
        self.inPipe = queue.Queue()
        self.outPipe = mesgPipe
        self.latency = 10_000_000_000
        self.collisions = 0
        self.cleanDiscoveries = 0
        self.numNeighbors = numNeighbors
        self.lastListenSartTime = 0
        self.DCUpdates = []
        self.finalDC = 0

        self._turnedOn = False
        self._slotOffset = slotOffset
        self._alignmentOffset = alignmentOffset
        self._cycleJustStarted = False
        self._startingTime = 0
        self._receivingMessage = False
        self._shouldStop = False

        self.setDutyCycle(dutycycle)

        self._DC = dutycycle
        self._activeSlots = 0

        self._newDiscoveriesMem = []
        self._collisionMem = []
        self._cleanDiscoveryMem = []
        self._totalDiscoveries = []

        self._discovered: Set[int] = set()
        self._discoveredTimes: List[int] = []
        self._collisionTimes: List[int] = []
        self._simStartTime = 0

        if not slotOffset:
            self.restart()

    def updateDutyCycle(self):
        self._cleanDiscoveryMem.append(self.cleanDiscoveries)
        if len(self._cleanDiscoveryMem) > 3:
            self._cleanDiscoveryMem = self._cleanDiscoveryMem[1:]

            if self._cleanDiscoveryMem[-1] == self._cleanDiscoveryMem[-2]:
                self._DC += 0.2
            elif len(self._cleanDiscoveryMem) >= 3 and self._cleanDiscoveryMem[-3] < self._cleanDiscoveryMem[-2] and self._cleanDiscoveryMem[-2] < self._cleanDiscoveryMem[-1]:
                self._DC -= 0.1


class Reward5NodeFactory(NodeFactory):
    def __init__(self, startDC=0.05, alpha=0.0546875) -> None:
        self.startDC = startDC
        self.alpha = alpha

    def produce(self, env, mesgPipe: simpy.Store, slotOffset=0, alignmentOffset=0, id=0, numNeighbors=0) -> Node:
        return Reward5Node(env, mesgPipe, slotOffset, self.startDC, alignmentOffset, self.alpha, id, numNeighbors)

    @property
    def nodeTypeName(self) -> str:
        return "Reward 5"


class Reward5Node(RewardNode):
    def __init__(self, env, mesgPipe: simpy.Store, slotOffset=0, dutycycle=0.05, alignmentOffset=0, alpha=0.0546875, id=0, numNeighbors=0) -> None:
        self.id = id
        self._alpha = alpha
        self._m = math.ceil(2 / dutycycle)
        self._n = math.ceil(alpha / dutycycle)
        self.listening = False
        self.transmitting = False
        self.env = env
        self.inPipe = queue.Queue()
        self.outPipe = mesgPipe
        self.latency = 10_000_000_000
        self.collisions = 0
        self.cleanDiscoveries = 0
        self.numNeighbors = numNeighbors
        self.lastListenSartTime = 0
        self.DCUpdates = []
        self.finalDC = 0

        self._turnedOn = False
        self._slotOffset = slotOffset
        self._alignmentOffset = alignmentOffset
        self._cycleJustStarted = False
        self._startingTime = 0
        self._receivingMessage = False
        self._shouldStop = False

        self.setDutyCycle(dutycycle)

        self._DC = dutycycle
        self._activeSlots = 0

        self._newDiscoveriesMem = []
        self._collisionMem = []
        self._cleanDiscoveryMem = []
        self._totalDiscoveries = []

        self._discovered: Set[int] = set()
        self._discoveredTimes: List[int] = []
        self._collisionTimes: List[int] = []
        self._simStartTime = 0

        if not slotOffset:
            self.restart()

    def updateDutyCycle(self):
        if len(self._totalDiscoveries) < 4:
            self._newDiscoveriesMem.append(len(self._discovered))

            if len(self._newDiscoveriesMem) <= 2:
                if self._newDiscoveriesMem[-1] == 0:
                    self._DC += 0.02
            elif len(self._newDiscoveriesMem) > 2:
                perfDiff = self.genDifferenceList(self._newDiscoveriesMem)
                if perfDiff[-1] == 0:
                    self._DC += 0.01 * len(self._newDiscoveriesMem)

        else:
            self._newDiscoveriesMem = self._perfList[1:]
            self._newDiscoveriesMem.append(len(self._discovered))

            perfDiff = self.genDifferenceList(self._newDiscoveriesMem)
            perf2Diff = self.genDifferenceList(perfDiff)

            if perf2Diff[1] <= 0.9 * perf2Diff[0]:
                self._DC += 0.04
            elif perf2Diff[1] >= 1.1 * perf2Diff[0]:
                self._DC -= 0.01


class RewardStaticNodeFactory(NodeFactory):
    # def __init__(self, startDC=0.05, alpha=0.0546875) -> None:
    def __init__(self, startDC=0.05, alpha=0.125) -> None:
    # def __init__(self, startDC=0.05, alpha=0.1) -> None:
        self.startDC = startDC
        self.alpha = alpha

    def produce(self, env, mesgPipe: simpy.Store, slotOffset=0, alignmentOffset=0, id=0, numNeighbors=0) -> Node:
        return RewardStaticNode(env, mesgPipe, slotOffset, self.startDC, alignmentOffset, self.alpha, id, numNeighbors)

    @property
    def nodeTypeName(self) -> str:
        return f"Reward static @{self.startDC}"


class RewardStaticNode(RewardNode):
    def __init__(self, env, mesgPipe: simpy.Store, slotOffset=0, dutycycle=0.05, alignmentOffset=0, alpha=0.0546875, id=0, numNeighbors=0) -> None:
        self.id = id
        self._alpha = alpha
        self._m = math.ceil(2 / dutycycle)
        self._n = math.ceil(alpha / dutycycle)
        self.listening = False
        self.transmitting = False
        self.env = env
        self.inPipeCount = 0
        self.inPipe = queue.Queue()
        self.outPipe = mesgPipe
        self.latency = 10_000_000_000
        self.collisions = 0
        self.cleanDiscoveries = 0
        self.numNeighbors = numNeighbors
        self.lastListenSartTime = 0
        self.DCUpdates = []
        self.finalDC = 0

        self._turnedOn = False
        self._slotOffset = slotOffset
        self._alignmentOffset = alignmentOffset
        self._cycleJustStarted = False
        self._startingTime = 0
        self._receivingMessage = False
        self._shouldStop = False

        self.setDutyCycle(dutycycle)

        self._DC = dutycycle
        self._activeSlots = 0

        self._newDiscoveriesMem = []
        self._collisionMem = []
        self._cleanDiscoveryMem = []
        self._totalDiscoveries = []

        self._discovered: Set[int] = set()
        self._discoveredTimes: List[int] = []
        self._collisionTimes: List[int] = []
        self._simStartTime = 0

        if not slotOffset:
            self.restart()

    def updateDutyCycle(self):
        self._DC = self._DC


class LCGNodeFactory(NodeFactory):
    def __init__(self, startDC=0.05, alpha=0.125) -> None:
        self.startDC = startDC
        self.alpha = alpha

    def produce(self, env, mesgPipe: simpy.Store, slotOffset=0, alignmentOffset=0, id=0, numNeighbors=0) -> Node:
        return LCGNode(env, mesgPipe, slotOffset, self.startDC, alignmentOffset, self.alpha, id, numNeighbors)

    @property
    def nodeTypeName(self) -> str:
        return f"Reward static @{self.startDC}"


class LCGNode(RewardNode):
    def __init__(self, env, mesgPipe: simpy.Store, slotOffset=0, dutycycle=0.05, alignmentOffset=0, alpha=0.0546875, id=0, numNeighbors=0) -> None:
        self.id = id
        self._alpha = alpha
        self._m = math.ceil(2 / dutycycle)
        self._n = math.ceil(alpha / dutycycle)
        self.listening = False
        self.transmitting = False
        self.env = env
        self.inPipeCount = 0
        self.inPipe = queue.Queue()
        self.outPipe = mesgPipe
        self.latency = 10_000_000_000
        self.collisions = 0
        self.cleanDiscoveries = 0
        self.numNeighbors = numNeighbors
        self.lastListenSartTime = 0
        self.DCUpdates = []
        self.finalDC = 0

        self._turnedOn = False
        self._slotOffset = slotOffset
        self._alignmentOffset = alignmentOffset
        self._cycleJustStarted = False
        self._startingTime = 0
        self._receivingMessage = False
        self._shouldStop = False

        self.setDutyCycle(dutycycle)

        self._DC = dutycycle
        self._activeSlots = 0

        self._newDiscoveriesMem = []
        self._collisionMem = []
        self._cleanDiscoveryMem = []
        self._totalDiscoveries = []

        self._discovered: Set[int] = set()
        self._discoveredTimes: List[int] = []
        self._collisionTimes: List[int] = []
        self._simStartTime = 0

        self.mod = 65536
        self.a = 137  # Standard multiplier for power-of-2 modulus
        self.c = 187  # Must be odd
        self.threshold = int(self._DC * self.mod)
        self.window_size = 100
        self.neighborTable = {}
        # self.neighborTable = {
        #     1: {'current_x': 1, 'last_time': 2},
        # }
        self.current_x = (self.id * 31337) % self.mod
        self.slot = 0

        if not slotOffset:
            self.restart()

    def updateDutyCycle(self):
        pass

    def doCycleStart(self):
        pass

    def receiveMessage(self, msg: Dict):
        # if self.id == 0:
            # print('Received: ', msg)
            # print('Listening: ', self.listening)

        cleanStart = True
        if not self.inPipe.empty():
            cleanStart = False

        sender = msg["from"]
        self.inPipe.put(sender)

        listeningFromTheStart = self.listening

        yield self.env.timeout(msg["alpha"])

        # Remove this new element after listening time is over
        _ = self.inPipe.get()

        cleanEnd = True
        if not self.inPipe.empty():
            cleanEnd = False

        if not listeningFromTheStart:
            return


        cleanDiscovery = cleanEnd and cleanStart
        newDiscovery = cleanDiscovery and sender not in self.neighborTable
        if newDiscovery:
            self._discovered.add(msg["from"])
            self.neighborTable[msg['from']] = {
                'current_x': msg['current_x'],
                'last_time': msg['slot']
            }

            if self.latency > 1_000_000_000_000 and self.hasDiscoveredAllNeighbors():
                self.latency = math.ceil(self.env.now)
                self.finalDC = self._DC

        elif cleanDiscovery:
            self.cleanDiscoveries += 1
        elif not cleanDiscovery:
            self.collisions += 1

    def hasDiscoveredAllNeighbors(self):
        return self.numNeighbors == len(self.neighborTable)

    def checkNeighborCollisions(self, slot_index):
        """Predicts if any neighbor is active at THIS specific slot."""
        for n_id in self.neighborTable.keys():

            neighbor = self.neighborTable[n_id]
            projected_x = neighbor['current_x']
            last_time = neighbor['last_time']
            for _ in range(last_time+1, slot_index+1):
                projected_x = (self.a * projected_x + self.c) % self.mod
            neighbor['last_time'] = slot_index
            neighbor['current_x'] = projected_x

            if projected_x < self.threshold:
                return True, n_id
        return False, None

    def doTX(self):
        msg = {
            "slot": self.slot,
            "current_x": self.current_x,
            "alpha": self._alpha,
            "from": self.id
        }

        self.listening = False
        self.transmitting = True
        self.outPipe.put(msg)
        yield self.env.timeout(self._alpha)
        self.transmitting = False

    def run(self, maxtime: int):
        yield self.env.timeout(self._startingTime)

        # self.current_x = (self.id * 31337) % self.mod
        self.current_x = int(random.random() * (2**16)-2)

        total = 0
        active = 0
        while self.env.now < maxtime and not self._shouldStop:
            self.current_x = (self.a * self.current_x + self.c) % self.mod
            self.slot = math.ceil(self.env.now)
            total += 1
            # if self.id != 0:
            #     print('time', self.env.now)
            if self.current_x <= self.threshold:
                active += 1
                # print(self.current_x, self.threshold)
                collision, culprit = self.checkNeighborCollisions(self.slot)
                if collision:
                    # print('aaa')
                    if random.random() < 0.5:
                        # TODO: make the shift dependent on curren number of neighbors
                        shift = (self.id % self.numNeighbors) + 1
                        start_delayed(self.env, self.activeSlotSequence(), shift)
                elif not self.listening and not self.transmitting:
                    # self.listening = False
                    # self.transmitting = True
                    self.env.process(self.activeSlotSequence())
                # self.env.process(self.activeSlotSequence())

            yield self.env.timeout(1)

        # print('eeeeeeeeeeeeeeee', active / total)
        self._discoveredTimes.sort()
        self._collisionTimes.sort()
        self.DCUpdates.sort()
