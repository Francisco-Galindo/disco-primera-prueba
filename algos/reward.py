import math
import random
import simpy
import simpy.core
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
        self.inPipe = []
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

        self._alignmentOffset = 0
        self._slotOffset = 0

        self.latency = 1_000_000_000

        if self.id != 0 and self.numNeighbors >= 1:
            self._alignmentOffset = random.uniform(0, 1)
            self._slotOffset = random.randint(0, self.T-1)

        self._startingTime = self._alignmentOffset + self._slotOffset

    def receiveMessage(self, msg: Dict):

        self._receivingMessage = True

        cleanStart = True
        if len(self.inPipe) != 0:
            cleanStart = False

        self.inPipe.append(msg["from"])
        # sender = msg["from"]
        # print(f"{self.env.now}: \t{self.id} is RECEIVING A MESSAGE from {sender}")
        # print(f"{self.env.now}: \t\t\t{self.id} receives message from {msg["from"]}")

        yield self.env.timeout(msg["alpha"])

        if self.env.now - self.lastListenSartTime > 1 - self.alpha:
            return

        # Remove this new element after listening time is over
        self.inPipe = list(filter(lambda x: x != msg["from"], self.inPipe))

        cleanEnd = True
        if len(self.inPipe) != 0:
            cleanEnd = False
        else:
            self._receivingMessage = False

        if cleanEnd and cleanStart and msg["from"] not in self._discovered:
            now = self.env.now

            self._discovered.add(msg["from"])
            self._discoveredTimes.append(math.ceil(now))

            if self.latency > 1_000_000 and self.hasDiscoveredAllNeighbors():
                self.latency = math.ceil(self.env.now)
                self.finalDC = self._activeSlots / self.latency
                # print("YA TERMINÉ", self.latency)
                # print(self.finalDC, self._DC) # !!!
                # print("DC", self._activeSlots / self.latency)

        elif cleanEnd and cleanStart:
            self.cleanDiscoveries += 1
        elif not cleanEnd or not cleanStart:
            # print("collision", self.env.now)
            self.collisions += 1
            self._collisionTimes.append(math.ceil(self.env.now))


    def hasDiscoveredAllNeighbors(self):
        return self.numNeighbors == len(self._discovered)

    def doTX(self):
        now = self.env.now
        timeToListen = 100000000000
        msg = {
            "now": now,
            "timeToListen": timeToListen,
            "alpha": self._alpha,
            "from": self.id
        }

        # if self.listening or self.transmitting:
        #     print("PAPEADO 2")
        #     return
        # while self._receivingMessage:
        #     yield self.env.timeout(self._alpha / 4)
        # print(f"{now}: \t{self.id} starts TX")
        self.listening = False
        self.transmitting = True
        self.outPipe.put(msg)
        yield self.env.timeout(self._alpha)
        self.transmitting = False
        # print(f"{self.env.now}: \t{self.id} stops TX")

    def updateDutyCycle(self):
        if len(self._totalDiscoveries) < 4:
            # self._newDiscoveriesMem.append(len(self._discovered))
            # self._collissionMemory.append(self.collisions)
            self._totalDiscoveries.append(self.cleanDiscoveries + self.collisions)

            if len(self._totalDiscoveries) <= 2:
                if self._totalDiscoveries[-1] == 0:
                    self._DC += 0.02
            elif len(self._totalDiscoveries) > 2:
                perfDiff = self.genDifferenceList(self._totalDiscoveries)
                if perfDiff[-1] == 0:
                    self._DC += 0.01 * len(self._totalDiscoveries)

        else:
            # self._newDiscoveriesMem = self._perfList[1:]
            # self._newDiscoveriesMem.append(len(self._discovered))
            # self._collissionMemory = self._collissionMemory[1:]
            # self._collissionMemory.append(self.collisions)
            self._totalDiscoveries = self._totalDiscoveries[1:]
            self._totalDiscoveries.append(self.cleanDiscoveries + self.collisions)

            perfDiff = self.genDifferenceList(self._totalDiscoveries)
            perf2Diff = self.genDifferenceList(perfDiff)

            if perf2Diff[1] <= 0.9 * perf2Diff[0]:
                self._DC += 0.04
            elif perf2Diff[1] >= 1.1 * perf2Diff[0]:
                self._DC -= 0.01


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

            beaconTimes.append(beaconTime)

        # if self.id == 0:
        #     print("LOLER", self._DC, self.env.now, len(beaconSlots), len(self._discovered))

        for beaconTime in beaconTimes:
            if beaconTime == 0:
                self.env.process(self.activeSlotSequence())
            else:
                start_delayed(self.env, self.activeSlotSequence(), beaconTime)
        # Won't run without it
        yield self.env.timeout(1)

    def activeSlotSequence(self):
        # if self.listening or self.transmitting:
        #     yield self.env.timeout(self.alpha)
        #     self._activeSlots -= 1
        #     print("PAPEADO")
        #     return
        self.env.process(self.doTX())
        yield self.env.timeout(self.alpha)
        self.env.process(self.doListen())

    def doListen(self):
        # print(f"{self.env.now}: \t{self.id} starts NORMAL LISTENING")
        self._cycleJustStarted = False
        self.lastListenSartTime = self.env.now
        self.listening = True
        yield self.env.timeout(1 - 2 * self.alpha)

        self.inPipe = []
        self.listening = False
        self.env.process(self.doTX())
        # print(f"{self.env.now}: \t{self.id} stops LISTENING")

    def run(self, maxtime: int):
        yield self.env.timeout(self._startingTime)

        for i in range(0, math.ceil(maxtime+1), 100):
            if i == 0:
                self.env.process(self.doCycleStart())
            else:
                start_delayed(self.env, self.doCycleStart(), i)

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
        self.inPipe = []
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
        self.inPipe = []
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
        self.inPipe = []
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
        self.inPipe = []
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
        self.inPipe = []
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
