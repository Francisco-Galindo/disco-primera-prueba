from functools import reduce
from itertools import accumulate
import math
import random

max_iterations = 10000

class SearchLightNode:

    def __init__(self, slotOffset = 0, dutycycle = 0.05, alignmentOffset = -1) -> None:
        self.setDutyCycle(dutycycle)
        self._probePos = 0
        self._turnedOn = False
        self._slotOffset = slotOffset
        self._alignmentOffset = alignmentOffset
        if not slotOffset:
            self.restart()


    def setDutyCycle(self, dutycycle = 0.05) -> None:
        self._t = math.floor(2 / dutycycle)

    def getDutyCycle(self) -> float:
        return 2 / self._t

    def getOffset(self) -> int:
        return self._slotOffset

    def updateProbePos(self):
        self._probePos = (self._probePos % math.floor(self._t / 2)) + 1

    def isTurnedOn(self) -> bool:
        return self._turnedOn

    def getT(self) -> int:
        return self._t

    def restart(self) -> None:
        self._slotOffset = random.randint(0, math.ceil(self._t / 2) + 1)


    def update(self, count, verbose=False) -> None:
        if self._alignmentOffset == -1 or count % 2 == self._alignmentOffset:

            if self._alignmentOffset != -1:
                count = int(count / 2)

            self._turnedOn = False
            if (count - self._slotOffset) % self._t == 0:
                self.updateProbePos()
                if verbose:
                    print('a', end='')
                self._turnedOn = True
            elif (count - self._slotOffset) % self._t == self._probePos:
                if verbose:
                    print('p', end='')
                self._turnedOn = True
            elif verbose:
                print('-', end='')


class SearchLightStripedNode(SearchLightNode):
    def updateProbePos(self):
        self._probePos = (self._probePos % (2 * math.ceil(math.floor(self._t / 2) / 2))) + 2


class SearchLightRandomNode(SearchLightNode):
    def __init__(self, slotOffset = 0, dutycycle = 0.05, alignmentOffset = -1):
        super().__init__(slotOffset, dutycycle, alignmentOffset)
        self._numbers = list(range(1, math.floor(self._t / 2) + 1))
        random.shuffle(self._numbers)
        self._firstTime = True
        self._index = 0

    def updateProbePos(self):
        if self._index < len(self._numbers) - 1:
            if not self._firstTime:
                self._index += 1
            else:
                self._firstTime = False
            # print('\n ', end='')
        else:
            self._index = 0
            random.shuffle(self._numbers)
            # print('\n*', end='')
        self._probePos = self._numbers[self._index]

class SearchLightStripedRandomNode(SearchLightNode):
    def __init__(self, slotOffset = 0, dutycycle = 0.05, alignmentOffset = -1):
        super().__init__(slotOffset, dutycycle, alignmentOffset)
        self._numbers = list(range(1, math.floor(self._t / 2) + 1, 2))
        random.shuffle(self._numbers)
        self._firstTime = True
        self._index = 0

    def updateProbePos(self):
        if self._index < len(self._numbers) - 1:
            if not self._firstTime:
                self._index += 1
            else:
                self._firstTime = False
            # print('\n ', end='')
        else:
            self._index = 0
            random.shuffle(self._numbers)
            # print('\n*', end='')
        self._probePos = self._numbers[self._index]


class DiscoNode:

    def __init__(self, primes = (), slotOffset = 0, dutycycle = 0.05, alignmentOffset=-1) -> None:
        self.nodeClass = 0
        self._primes = primes
        if not self._primes:
            self.setDutyCycle(dutycycle)
        if not slotOffset:
            self.restart()
        self._slotOffset = slotOffset
        self._alignmentOffset = alignmentOffset

    def setDutyCycle(self, dutycycle = 0.05) -> None:
        possiblePrimes = [(23, 157), (29, 67), (31, 59), (37, 43)]
        self._primes = random.choice(possiblePrimes)

    def getDutyCycle(self) -> float:
        return reduce(lambda x, y: x + 1 / y, self._primes, 0)

    def getPrimes(self):
        return self._primes

    def getSlotOffset(self) -> int:
        return self._slotOffset

    def restart(self) -> None:
        self._slotOffset = random.randint(0, reduce(lambda x, y: x * y, self._primes))


    def isTurnedOn(self) -> bool:
        return self._turnedOn

    def update(self, count) -> None:
        if self._alignmentOffset != -1:
            count = int(count / 2)
        for prime in self._primes:
            self._turnedOn = False
            if (count - self._slotOffset) % prime == 0:
                self._turnedOn = True
                return


class Algorithm:
    def __init__(self, nodes, name, aligned=True) -> None:
        self._nodes = nodes
        self._name = name
        self._aligned = aligned

    def getName(self) -> str:
        return self._name

    def getNodes(self):
        return self._nodes

    def getLatency(self):
        if self._aligned:
            return self.getAlignedLatency()
        return self.getMissAlignedLatency()

    def getAlignedLatency(self, max=max_iterations):
        count = 0
        found = False
        while not found and count < max - 1:
            found = True
            for node in self._nodes:
                node.update(count)
                if not node.isTurnedOn():
                    found = False
                    # break

            count += 1

        for node in self._nodes:
            node.restart()

        return count

    def getMissAlignedLatency(self):
        return int(self.getAlignedLatency(max_iterations*2) / 2)


class Test:
    def __init__(self, algorithms, numTests = 1000) -> None:
        self.algorithms = algorithms
        self.numTests = numTests
        self.testResults = {}

    def run(self):
        for algorithm in self.algorithms:
            discoveries = [0] * max_iterations
            for _ in range(self.numTests):
                latency = algorithm.getLatency()
                discoveries[latency] += 1

            accumDiscoveries = list(accumulate(discoveries))

            cdf = list(map(lambda x: x / self.numTests, accumDiscoveries))
            self.testResults[algorithm.getName()] = cdf


        return self.testResults
