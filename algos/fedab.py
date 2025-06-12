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

    def txToNeighbors(self, nextListenAbsTime):
        for neighbor in self.neighbors:
            if neighbor.listening:
                neighbor.discovered.add(self.id)
                neighbor.addTxTime(nextListenAbsTime)
                # print('hello from', self.id, neighbor.id, nextListenAbsTime)
                # print(f'hello from {self.id}, {neighbor.id}!\t do extra_tx at: {nextListenAbsTime}')

    def hasDiscoveredAllNeighbors(self):
        return len(self.neighbors) == len(self.discovered)

    def run(self, env, beaconPipe, listenPipe):
        startingTime = self._alignmentOffset + self._slotOffset
        yield env.timeout(startingTime)

        i = 0
        # print('EEEEEEEEEEEEEEEE\t started', self.id, env.now, i, self._m, self._n, self.getT())

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

                # print(self.id, '\t start_tx at', env.now)

                self.txToNeighbors(nextListenAbsTime)
                yield env.timeout(self._alpha)
                self.txToNeighbors(nextListenAbsTime)

                # print(self.id, '\t end_tx at', env.now)

                yield env.timeout(remainingSlotTime)

            else:
                remainingSlotTime = 1
                # print('extratime', self._extraTxTimes, self.id)
                for time in self._extraTxTimes:
                    if 0 <= (env.now - time) < 1:
                        timeToNextListen = self._m - (i % self._m)
                        nextListenAbsTime = env.now + timeToNextListen

                        # print(self.id, '\t start_extra_tx at', env.now)

                        self.txToNeighbors(nextListenAbsTime)

                        yield env.timeout(self._alpha)
                        remainingSlotTime -= - self._alpha

                        self.txToNeighbors(nextListenAbsTime)

                        # print(self.id, '\t end_extra_tx at', env.now)

                        break

                if i % self._m == 0:

                    # print(self.id, '\t start_rx at', env.now)

                    self.listening = True

                    yield env.timeout(remainingSlotTime)

                    self.listening = False

                    # print(self.id, '\t end_rx at', env.now)

                    if self.hasDiscoveredAllNeighbors():
                        # print(self.id, 'I', i, "NOW", env.now)
                        self.latency = i

                else:
                    yield env.timeout(remainingSlotTime)

            i += 1
