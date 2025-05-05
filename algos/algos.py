from functools import reduce
from itertools import accumulate
import math
import random
import simpy
import simpy.core
import simpy.util

class SearchLightNode:

    def __init__(self, slotOffset = 0, dutycycle = 0.05, alignmentOffset = 0) -> None:
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

    def getAlignment(self) -> float:
        return self._alignmentOffset

    def updateProbePos(self):
        self._probePos = (self._probePos % math.floor(self._t / 2)) + 1

    def isTurnedOn(self) -> bool:
        return self._turnedOn

    def getT(self) -> int:
        return self._t

    def restart(self) -> None:
        self._slotOffset = random.randint(0, math.ceil(self._t / 2) + 1)
        self.latency = 1_000_000_000
        self._alignmentOffset = random.random()


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
    def run(self, env, beaconPipe, listenPipe):
        startingTime = self._alignmentOffset + self._slotOffset
        yield env.timeout(startingTime)
        nextPivot = startingTime
        found = False
        while not found:
            yield env.timeout(nextPivot - env.now)
            msg = env.now
            beaconPipe.append(msg)
            yield env.timeout(1)
            msg = env.now
            beaconPipe.append(msg)

            self.updateProbePos()
            nextProbe = nextPivot + self._probePos

            yield env.timeout(nextProbe - env.now)
            msg = env.now
            beaconPipe.append(msg)
            yield env.timeout(1)
            msg = env.now
            beaconPipe.append(msg)

            while listenPipe:
                msg = listenPipe.pop()
                if nextProbe <= msg <= (nextProbe + 1) or nextPivot <= msg <= (nextPivot + 1):
                    self.latency = msg
                    found = True


            nextPivot += self._t


class SearchLightStripedNode(SearchLightNode):
    def updateProbePos(self):
        self._probePos = (self._probePos % (2 * math.ceil(math.floor(self._t / 2) / 2))) + 2


class SearchLightRandomNode(SearchLightNode):
    def __init__(self, slotOffset = 0, dutycycle = 0.05, alignmentOffset = 0):
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
    def __init__(self, slotOffset = 0, dutycycle = 0.05, alignmentOffset = 0):
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

    def __init__(self, primes = (), slotOffset = 0, dutycycle = 0.05, name = 'A') -> None:
        self.nodeClass = 0
        self._primes = primes
        self._name = name
        if not self._primes:
            self.setDutyCycle(dutycycle)

        self.restart()

        if slotOffset != 0:
            self._slotOffset = slotOffset

    def setDutyCycle(self, dutycycle = 0.05) -> None:
        possiblePrimes = [(23, 157), (29, 67), (31, 59), (37, 43)]
        self._primes = random.choice(possiblePrimes)

    def getDutyCycle(self) -> float:
        return reduce(lambda x, y: x + 1 / y, self._primes, 0)

    def getPrimes(self):
        return self._primes

    def getSlotOffset(self) -> int:
        return self._slotOffset

    def getAlignment(self) -> float:
        return self._alignmentOffset


    def restart(self) -> None:
        self._slotOffset = 0
        self._alignmentOffset = 0

        if self._name == 'B':
            self._slotOffset = random.randint(0, math.floor(reduce(lambda x, y: x * y, self._primes)))
            n = random.randint(1, 1023)
            self._alignmentOffset = n / (2**10)

        self.latency = 1_000_000_000

    def run(self, env, beaconPipe, listenPipe):
        smallPrime = max(self._primes)
        bigPrime = min(self._primes)
        timeToSmallPrime = 0
        timeToBigPrime = 0

        # if self._name == 'B':
        #     print("AS")
        found = False
        lastTurnOn = 0
        cnt = 0
        while not found:
            waitingTime = min(timeToBigPrime, timeToSmallPrime)
            yield env.timeout(waitingTime)
            lastTurnOn = env.now
            cnt += 1
            # if self._name == 'B':
            # print(self._name, lastTurnOn)
            beaconPipe.append(lastTurnOn)
            yield env.timeout(1)
            beaconPipe.append(lastTurnOn+1)

            timeToSmallPrime -= waitingTime + 1
            timeToBigPrime -= waitingTime + 1

            if timeToSmallPrime < 0:
                timeToSmallPrime = smallPrime - 1
            if timeToBigPrime < 0:
                timeToBigPrime = bigPrime - 1

            while listenPipe:
                msg = listenPipe.pop()
                if lastTurnOn < msg < lastTurnOn + 1:
                    found = True
                    # if self._name == 'B':
                    #     self.latency = msg - self._slotOffset
                    # else:
                    self.latency = msg - self._slotOffset

                    # # print('yea', self.latency)
                    # dc = round(cnt / self.latency, 2)
                    # # print(self._name, dc)
                    # if dc > 0.9 and self._name == 'B':
                    #     print('PAPU', lastTurnOn, env.now, self._alignmentOffset, self._slotOffset)
                    break


class Algorithm:
    def __init__(self, nodeA, nodeB, name) -> None:
        self._nodeA = nodeA
        self._nodeB = nodeB
        self._name = name

    def getName(self) -> str:
        return self._name

    def getLatency(self, maxTime):
        self._nodeA.restart()
        self._nodeB.restart()

        offset = self._nodeB.getSlotOffset()
        alignmentOffset = self._nodeB.getAlignment()

        env = simpy.Environment()
        pipeA = []
        pipeB = []

        env.process(self._nodeA.run(env, pipeA, pipeB))
        # env.process(self._nodeB.run(env, pipeB, pipeA))
        simpy.util.start_delayed(env, self._nodeB.run(env, pipeB, pipeA), offset + alignmentOffset)

        env.run(until=maxTime+offset)

        return math.ceil(min(self._nodeA.latency, self._nodeB.latency, maxTime-1))


class Test:
    def __init__(self, algorithms, numTests = 1000, maxTime = 2000) -> None:
        self.algorithms = algorithms
        self.numTests = numTests
        self.testResults = {}
        self.maxTime = maxTime

    def run(self):
        for algorithm in self.algorithms:
            discoveries = [0] * self.maxTime
            for i in range(self.numTests):
                # print(i)
                latency = algorithm.getLatency(self.maxTime)
                discoveries[latency] += 1

            accumDiscoveries = list(accumulate(discoveries))

            cdf = list(map(lambda x: x / self.numTests, accumDiscoveries))
            self.testResults[algorithm.getName()] = cdf

        return self.testResults
