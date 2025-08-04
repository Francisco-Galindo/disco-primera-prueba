import math
import random
import simpy
import simpy.core
from simpy.util import start_delayed
from algos.node import Node, NodeFactory
from typing import Dict


class FedabNodeFactory(NodeFactory):
    def __init__(self, dutyCycle=0.05, alpha=0.0546875) -> None:
        self.dutyCycle = dutyCycle
        self.alpha = alpha

    def produce(self, env, mesgPipe: simpy.Store, slotOffset=0, alignmentOffset=0, id=0, numNeighbors=0) -> Node:
        return FedabNode(env, mesgPipe, slotOffset, self.dutyCycle, alignmentOffset, self.alpha, id, numNeighbors)


class FedabNode(Node):
    def __init__(self, env, mesgPipe: simpy.Store, slotOffset=0, dutycycle=0.05, alignmentOffset=0, alpha=0.0546875, id=0, numNeighbors=0) -> None:
        self.id = id
        self._alpha = alpha
        self._m = math.ceil(2 / dutycycle)
        self._n = math.ceil(alpha / dutycycle)
        self.listening = False
        self.env = env
        self.inPipe = []
        self.outPipe = mesgPipe
        self.latency = 10000000000
        self.numNeighbors = numNeighbors
        self.lastListenSartTime = 0

        self._turnedOn = False
        self._slotOffset = slotOffset
        self._alignmentOffset = alignmentOffset
        self._cycleJustStarted = False
        self._startingTime = 0
        self.setDutyCycle(dutycycle)

        # self._n = 3
        # self._m = 5

        self.discovered = set()
        self._extraTxTimes = []

        if not slotOffset:
            self.restart()

    def setDutyCycle(self, dutycycle=0.05) -> None:
        self._m = math.ceil(2 / dutycycle)
        self._n = math.ceil(self._alpha / dutycycle)
        # print("m, n:\t", self._m, self._n)

    def getDutyCycle(self) -> float:
        return 2 / self._m

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
        return len(self.discovered)

    def restart(self) -> None:
        self.discovered = set()
        self._extraTxTimes = []
        self.listening = False

        self._alignmentOffset = 0
        self._slotOffset = 0

        self.latency = 1_000_000_000

        if self.id != 0 and self.numNeighbors >= 1:
            # print("RANDOMIZANDO desde ", self.id)
            self._alignmentOffset = random.random()
            # self._alignmentOffset = random.random() * (1 - 2*self._alpha) + self._alpha
            self._slotOffset = random.randint(0, self.T-1)

            # self._alignmentOffset = 0.5
            # self._slotOffset = 0

            # self._alignmentOffset = 0.05099956982122078
            # self._slotOffset = 75

            self._alignmentOffset = 0.966
            self._slotOffset = 4

        self._startingTime = self._alignmentOffset + self._slotOffset

    def receiveMessage(self, msg: Dict):

        cleanStart = True
        if len(self.inPipe) != 0:
            cleanStart = False

        self.inPipe.append(msg["from"])
        sender = msg["from"]
        print(f"{self.env.now}: \t{self.id} is RECEIVING A MESSAGE from {sender}")
        # print(f"{self.env.now}: \t\t\t{self.id} receives message from {msg["from"]}")

        yield self.env.timeout(msg["alpha"])

        # Remove this new element after listening time is over
        self.inPipe = list(filter(lambda x: x != msg["from"], self.inPipe))

        cleanEnd = True
        if len(self.inPipe) != 0:
            cleanEnd = False

        if cleanEnd and cleanStart and msg["from"] not in self.discovered:
            self.discovered.add(msg["from"])

            now = self.env.now

            if self.latency > 1_000_000:
                # print("YA TERMINÉ")
                self.latency = math.ceil(self.env.now)

            traversedTime = now - self._startingTime
            timeToFinishSlot = 1 - (traversedTime % 1)
            start_delayed(self.env,
                          self.doTX(),
                          msg["timeToListen"] + timeToFinishSlot - self._alpha)

        # If isten time exceeded, this functions handles finishing the
        # listening window.
        if self.env.now - self.lastListenSartTime > 1 and (self.inPipe) == 0:
            yield self.env.timeout(self._alpha)
            self.listening = False
            # print(f"{self.env.now}: \t{self.id} stops LISTENING")
            if self._cycleJustStarted:
                self.env.process(self.doTX())

    def hasDiscoveredAllNeighbors(self):
        return self.numNeighbors == len(self.discovered)

    def doTX(self):
        now = self.env.now
        traversedTime = now - self._startingTime
        timeToListen = self._m - (traversedTime % self._m)
        msg = {
            "now": now,
            "timeToListen": timeToListen,
            "alpha": self._alpha,
            "from": self.id
        }

        if self.listening:
            print(f"{now}: \t{self.id} stops LISTENING")
        print(f"{now}: \t{self.id} starts TX")
        self.listening = False
        self.outPipe.put(msg)
        yield self.env.timeout(self._alpha)
        print(f"{self.env.now}: \t{self.id} stops TX")

    def doCycleStart(self):
        print(f"{self.env.now}: \t{self.id} starts FIRST LISTENING")
        self.lastListenSartTime = self.env.now
        self._cycleJustStarted = True

        for i in range(1, math.ceil(self._m / 2)+1):
            start_delayed(self.env, self.doTX(), i - self._alpha)

        self.listening = True
        yield self.env.timeout(1)
        if len(self.inPipe) == 0 and self.listening:
            print(f"{self.env.now}: \t{self.id} stops FIRST LISTENING")
            self.listening = False

        # # If there are elements in inPipe, let receiveMessage handle that.
        # if len(self.inPipe) == 0:
        #     self.listening = False
        #     # print(f"{self.env.now}: \t{self.id} stops LISTENING")
        #     self.env.process(self.doTX())

    def doNormalListen(self):
        print(f"{self.env.now}: \t{self.id} starts NORMAL LISTENING")
        self._cycleJustStarted = False
        self.lastListenSartTime = self.env.now
        self.listening = True
        yield self.env.timeout(1)
        # If there are elements in inPipe, let receiveMessage handle that.
        if len(self.inPipe) == 0:
            self.listening = False
            print(f"{self.env.now}: \t{self.id} stops LISTENING")

    def run(self, maxtime: int):
        startingTime = self._alignmentOffset + self._slotOffset
        yield self.env.timeout(startingTime)

        for i in range(0, math.ceil(maxtime+1), self._m):
            if i == 0:
                self.env.process(self.doCycleStart())
            elif i % self.T == 0:
                start_delayed(self.env, self.doCycleStart(), i)
            else:
                start_delayed(self.env, self.doNormalListen(), i)


class FedabStochasticNodeFactory(NodeFactory):
    def __init__(self, dutyCycle=0.05, alpha=0.0546875) -> None:
        self.dutyCycle = dutyCycle
        self.alpha = alpha

    def produce(self, env, mesgPipe: simpy.Store, slotOffset=0, alignmentOffset=0, id=0, numNeighbors=0) -> Node:
        return FedabStochasticNode(env, mesgPipe, slotOffset, self.dutyCycle, alignmentOffset, self.alpha, id, numNeighbors)


class FedabStochasticNode(FedabNode):
    def __init__(self, env, mesgPipe: simpy.Store, slotOffset=0, dutycycle=0.05, alignmentOffset=0, alpha=0.0546875, id=0, numNeighbors=0) -> None:
        super().__init__(env, mesgPipe, slotOffset, dutycycle, alignmentOffset, alpha, id, numNeighbors)
        self.updateBeaconTimes()
        self._beaconTimes = []

    def updateBeaconTimes(self):
        self._beaconTimes = []
        cols = random.sample([x for x in range(1, self._m+1)], math.ceil(self._m / 2))
        usedRows = [-1]
        for i in range(len(cols)):
            row = -1
            while row in usedRows:
                row = random.randint(0, self._n - 1)
            if len(cols) <= self._n:
                usedRows.append(row)
            self._beaconTimes.append(self._m * row + cols[i])

    def doCycleStart(self):
        # print(f"{self.env.now}: \t{self.id} starts FIRST LISTENING")
        self.lastListenSartTime = self.env.now
        self._cycleJustStarted = True
        # yield self.env.timeout(1-self._alpha)

        self.updateBeaconTimes()
        for i in self._beaconTimes:
            start_delayed(self.env, self.doTX(), i - self._alpha)

        self.listening = True
        yield self.env.timeout(1)
        if len(self.inPipe) == 0:
            self.listening = False

# # class FedabStochasticNode2(FedabStochasticNode):
# #     def __init__(self, slotOffset = 0, dutycycle = 0.05, alignmentOffset = 0, alpha = 0.0546875, id = 0, neighbors = []) -> None:
# #         super().__init__(slotOffset, dutycycle, alignmentOffset, alpha, id, neighbors)
# #         self.updateBeaconTimes()
# #         self._beaconTimes = []

# #     def updateBeaconTimes(self):
# #         self._beaconTimes = []
# #         cols = random.sample([x for x in range(self._m)], math.ceil(self._m / 2))
# #         for i in range(len(cols)):
# #             num = random.randint(0, self._n - 1)
# #             self._beaconTimes.append(self._m * num + cols[i])
