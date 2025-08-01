import math
import random
import simpy
import simpy.core
import simpy.util

class FedabNode:

    def __init__(self, slotOffset = 0, dutycycle = 0.05, alignmentOffset = 0, alpha = 0.054, id = 0, neighbors = []) -> None:
        self.id = id
        self._alpha = alpha
        self._m = math.ceil(2 / dutycycle)
        self._n = math.ceil(alpha / dutycycle)
        self.listening = False

        self._turnedOn = False
        self._slotOffset = slotOffset
        self._alignmentOffset = alignmentOffset
        self.setDutyCycle(dutycycle)

        # self._n = 3
        # self._m = 5

        self.neighbors = neighbors
        self.discovered = set()
        self._extraTxTimes = []

        if not slotOffset:
            self.restart()

    def setDutyCycle(self, dutycycle = 0.05) -> None:
        self._m = math.ceil(2 / dutycycle)
        self._n = math.ceil(self._alpha / dutycycle)

    def getDutyCycle(self) -> float:
        return 2 / self._m

    def getSlotOffset(self) -> int:
        return self._slotOffset

    def getOffset(self) -> int:
        return self._slotOffset

    def getAlignment(self) -> float:
        return self._alignmentOffset

    def isTurnedOn(self) -> bool:
        return self._turnedOn

    def getM(self) -> int:
        return self._m

    def getN(self) -> int:
        return self._n

    def getT(self) -> int:
        return self._n * self._m

    def setSimDelay(self, t: float) -> None:
        self._simDelay = t

    def addTxTime(self, newTime):
        # print('antes', self._extraTxTimes, self.id)
        self._extraTxTimes.append(newTime)
        # print('despues', self._extraTxTimes, self.id)

    def setNeigbors(self, neighbors):
        self.neighbors = neighbors

    def restart(self) -> None:
        self.discovered = set()
        self._extraTxTimes = []
        self.listening = False

        self._alignmentOffset = 0
        self._slotOffset = 0

        # self._alignmentOffset = 0.50
        # self._slotOffset = 654

        # self._alignmentOffset = 0.554
        # self._slotOffset = 12

        self.latency = 1_000_000_000

        if self.id != 0 and self.neighbors:
            self._alignmentOffset = random.random()
            self._slotOffset = random.randint(0, math.ceil(self.neighbors[0].getT()))

            # self._alignmentOffset = 0.88
            # self._slotOffset = 1014

            # self._slotOffset = 0

            # self._alignmentOffset = 0.2109
            # self._slotOffset = 5

            # self._alignmentOffset = 0.2961743601654
            # self._slotOffset = 534

    def txToNeighbors(self, nextListenAbsTime, currTime):
        if currTime < self._simDelay:
            return

        for neighbor in self.neighbors:
            if neighbor.listening:
                neighbor.discovered.add(self.id)
                neighbor.addTxTime(nextListenAbsTime)

    def hasDiscoveredAllNeighbors(self):
        return len(self.neighbors) == len(self.discovered)

    def run(self, env, beaconPipe, listenPipe):
        startingTime = self._alignmentOffset + self._slotOffset
        yield env.timeout(startingTime)

        i = 0

        while True:
            if self.hasDiscoveredAllNeighbors():
                done = True
                for neighbor in self.neighbors:
                    if not neighbor.hasDiscoveredAllNeighbors():
                        done = False
                        break

                if done:
                    break

            if 1 <= i % self.getT() <= math.ceil(self._m / 2):
                timeToNextListen = self._m - (i % self._m)
                nextListenAbsTime = env.now + timeToNextListen

                remainingSlotTime = 1 - self._alpha

                self.txToNeighbors(nextListenAbsTime, i)
                yield env.timeout(self._alpha)
                self.txToNeighbors(nextListenAbsTime, i)

                yield env.timeout(remainingSlotTime, i)

            else:
                remainingSlotTime = 1
                for time in self._extraTxTimes:
                    if 0 <= (env.now - time) < 1:
                        timeToNextListen = self._m - (i % self._m)
                        nextListenAbsTime = env.now + timeToNextListen

                        self.txToNeighbors(nextListenAbsTime, i)

                        yield env.timeout(self._alpha)
                        remainingSlotTime -= - self._alpha

                        self.txToNeighbors(nextListenAbsTime, i)

                        break

                if i % self._m == 0:

                    self.listening = True

                    yield env.timeout(remainingSlotTime)

                    self.listening = False

                    if self.hasDiscoveredAllNeighbors():
                        self.latency = i - self._simDelay

                else:
                    yield env.timeout(remainingSlotTime)

            i += 1


class FedabStochasticNode(FedabNode):
    def __init__(self, slotOffset = 0, dutycycle = 0.05, alignmentOffset = 0, alpha = 0.054, id = 0, neighbors = []) -> None:
        super().__init__(slotOffset, dutycycle, alignmentOffset, alpha, id, neighbors)
        self.updateBeaconTimes()
        self._beaconTimes = []

    def updateBeaconTimes(self):
        self._beaconTimes = []
        # print('andorra', self._beaconTimes)
        for i in range(1, self._m):
            num = random.randint(0, self._n - 1)
            self._beaconTimes.append(self._m * num + i)

    def run(self, env, beaconPipe, listenPipe):
        startingTime = self._alignmentOffset + self._slotOffset
        yield env.timeout(startingTime)

        i = 0

        while True:
            if self.hasDiscoveredAllNeighbors():
                done = True
                for neighbor in self.neighbors:
                    if not neighbor.hasDiscoveredAllNeighbors():
                        done = False
                        break

                if done:
                    break

            # if self.id == 0:
            #     print("MODULO", i % self.getT())
            if i % self.getT() == 0:
                # if self.id == 0:
                #     print("UpdateBEACONTIME")
                self.updateBeaconTimes()

            # print(self._beaconTimes, self.getT())
            if i % self.getT() in self._beaconTimes:
                timeToNextListen = self._m - (i % self._m)
                nextListenAbsTime = env.now + timeToNextListen

                remainingSlotTime = 1 - self._alpha

                self.txToNeighbors(nextListenAbsTime, i)
                yield env.timeout(self._alpha)
                self.txToNeighbors(nextListenAbsTime, i)

                yield env.timeout(remainingSlotTime, i)

            else:
                remainingSlotTime = 1
                for time in self._extraTxTimes:
                    if 0 <= (env.now - time) < 1:
                        timeToNextListen = self._m - (i % self._m)
                        nextListenAbsTime = env.now + timeToNextListen

                        self.txToNeighbors(nextListenAbsTime, i)

                        yield env.timeout(self._alpha)
                        remainingSlotTime -= - self._alpha

                        self.txToNeighbors(nextListenAbsTime, i)

                        break

                if i % self._m == 0:

                    self.listening = True

                    yield env.timeout(remainingSlotTime)

                    self.listening = False

                    if self.hasDiscoveredAllNeighbors():
                        self.latency = i - self._simDelay

                else:
                    yield env.timeout(remainingSlotTime)

            i += 1


class FedabStochasticNode2(FedabStochasticNode):
    def __init__(self, slotOffset = 0, dutycycle = 0.05, alignmentOffset = 0, alpha = 0.054, id = 0, neighbors = []) -> None:
        super().__init__(slotOffset, dutycycle, alignmentOffset, alpha, id, neighbors)
        self.updateBeaconTimes()
        self._beaconTimes = []

    def updateBeaconTimes(self):
        self._beaconTimes = []
        cols = random.sample([x for x in range(self._m)], math.ceil(self._m / 2))
        for i in range(len(cols)):
            num = random.randint(0, self._n - 1)
            self._beaconTimes.append(self._m * num + cols[i])
