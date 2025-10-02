import math
import random
import simpy
import simpy.core
from simpy.util import start_delayed
from algos.node import Node, NodeFactory
from typing import Dict, TypedDict, Set, List


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
        return "Reward"


class RewardNode(Node):
    def __init__(self, env, mesgPipe: simpy.Store, slotOffset=0, dutycycle=0.05, alignmentOffset=0, alpha=0.0546875, id=0, numNeighbors=0) -> None:
        self.id = id
        self._alpha = alpha
        self._m = math.ceil(2 / dutycycle)
        self._n = math.ceil(alpha / dutycycle)
        self.listening = False
        self.env = env
        self.inPipe = []
        self.outPipe = mesgPipe
        self.latency = 10_000_000_000
        self.collisions = 0
        self.numNeighbors = numNeighbors
        self.lastListenSartTime = 0

        self._turnedOn = False
        self._slotOffset = slotOffset
        self._alignmentOffset = alignmentOffset
        self._cycleJustStarted = False
        self._startingTime = 0
        self._receivingMessage = False

        self.setDutyCycle(dutycycle)

        self._DC = dutycycle
        self._activeSlots = 0

        self._perfList = []
        self._perfDiff = []
        self._perf2Diff = []

        self._discovered: Set[int] = set()
        self._discoveredTimes: List[int] = []

        if not slotOffset:
            self.restart()

    def setDutyCycle(self, dutycycle=0.05) -> None:
        # self._m = math.ceil(2 / dutycycle)
        # self._n = math.ceil(self._alpha / dutycycle)
        pass

    def getDutyCycle(self) -> float:
        return 2 / self._m

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
        return self._n * self._m

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
                # print("YA TERMINÉ")
                self.latency = math.ceil(self.env.now)
                print(self._activeSlots / self.latency)

        # elif not cleanEnd or not cleanStart:
        #     print("collision")

        # If isten time exceeded, this functions handles finishing the
        # listening window.
        if self.env.now - self.lastListenSartTime > 1 - 2*self.alpha and (self.inPipe) == 0:
            yield self.env.timeout(self._alpha)
            self.listening = False
            # print(f"{self.env.now}: \t{self.id} stops LISTENING")
            self.env.process(self.doTX())

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

        # if self.listening:
            # print(f"{now}: \t{self.id} stops LISTENING")
        if self._receivingMessage:
            self.collisions += 1
        # while self._receivingMessage:
        #     yield self.env.timeout(self._alpha / 4)
        # print(f"{now}: \t{self.id} starts TX")
        self.listening = False
        self.outPipe.put(msg)
        yield self.env.timeout(self._alpha)
        # print(f"{self.env.now}: \t{self.id} stops TX")

    def updateDutyCycle(self):
        if len(self._perfList) < 4:
            self._perfList.append(len(self._discovered))

            if len(self._perfList) <= 2:
                if self._perfList[-1] == 0:
                    self._DC += 0.02
            elif len(self._perfList) > 2:
                self._perfDiff = self.genDifferenceList(self._perfList)
                if self._perfDiff[-1] == 0:
                    self._DC += 0.01 * len(self._perfList)

        else:
            self._perfList = self._perfList[1:]
            self._perfList.append(len(self._discovered))

            self._perfDiff = self.genDifferenceList(self._perfList)
            self._perf2Diff = self.genDifferenceList(self._perfDiff)

            if self._perf2Diff[1] <= 0.9 * self._perf2Diff[0]:
                # if self.id == 0:
                #     print("YEA")
                self._DC += 0.02
                # try:
                #     self._DC += min(self._perf2Diff[0] / self._perf2Diff[1] * 0.04, 0.05)
                # except ZeroDivisionError:
                #     self._DC += 0.05
            elif self._perf2Diff[1] >= 1.1 * self._perf2Diff[0]:
                self._DC -= 0.01

    def genDifferenceList(self, lst):
        return [lst[i+1] - lst[i] for i in range(len(lst)-1)]

    def doCycleStart(self):
        # print(f"{self.env.now}: \t{self.id} starts FIRST LISTENING")
        self.lastListenSartTime = self.env.now
        self._cycleJustStarted = True

        self.updateDutyCycle()

        self._DC = max(0.01, self._DC)
        self._DC = min(0.13, self._DC)
        self._activeSlots += self._DC * 100

        beaconSlots = []
        for i in range(round(self._DC / 0.01)):
            beaconSlot = random.randint(0, 99)
            while beaconSlot in beaconSlots:
                beaconSlot = random.randint(0, 99)

            beaconSlots.append(beaconSlot)

        # if self.id == 0:
        #     print("LOLER", self._DC, self.env.now, len(beaconSlots), len(self._discovered))

        for beaconSlot in beaconSlots:
            if beaconSlot == 0:
                self.env.process(self.activeSlotSequence())
            else:
                start_delayed(self.env, self.activeSlotSequence(), beaconSlot)
        yield self.env.timeout(1) # LOL

    def activeSlotSequence(self):
        self.env.process(self.doTX())
        yield self.env.timeout(self.alpha)
        self.env.process(self.doListen())

    def doListen(self):
        # print(f"{self.env.now}: \t{self.id} starts NORMAL LISTENING")
        self._cycleJustStarted = False
        self.lastListenSartTime = self.env.now
        self.listening = True
        yield self.env.timeout(1 - 2 * self.alpha)
        # If there are elements in inPipe, let receiveMessage handle that.
        if len(self.inPipe) == 0:
            self.env.process(self.doTX())
            self.listening = False
            # print(f"{self.env.now}: \t{self.id} stops LISTENING")

    def run(self, maxtime: int):
        yield self.env.timeout(self._startingTime)

        for i in range(0, math.ceil(maxtime+1), 100):
            if i == 0:
                self.env.process(self.doCycleStart())
            else:
                start_delayed(self.env, self.doCycleStart(), i)

        self._discoveredTimes.sort()
