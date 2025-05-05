from functools import reduce
from itertools import accumulate
import math
import random
import simpy
import simpy.core
import simpy.util

class SearchLightNode:

    def __init__(self, slotOffset = 0, dutycycle = 0.05, alignmentOffset = 0, name = 'A', otherNode = None) -> None:
        self.setDutyCycle(dutycycle)
        self._probePos = 0
        self._turnedOn = False
        self._slotOffset = slotOffset
        self._alignmentOffset = alignmentOffset
        self._name = name
        if not slotOffset:
            self.restart(otherNode)


    def setDutyCycle(self, dutycycle = 0.05) -> None:
        self._t = math.floor(2 / dutycycle)

    def getDutyCycle(self) -> float:
        return 2 / self._t

    def getSlotOffset(self) -> int:
        return self._slotOffset

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

    def restart(self, otherNode = None) -> None:
        self._alignmentOffset = 0
        self._slotOffset = 0
        self.latency = 1_000_000_000

        if self._name == 'B' and otherNode:
            self._alignmentOffset = random.random()
            self._slotOffset = random.randint(0, math.ceil(otherNode.getT() / 2) + 1)


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
                    self.latency = msg - startingTime
                    found = True


            nextPivot += self._t


class SearchLightStripedNode(SearchLightNode):
    def updateProbePos(self):
        self._probePos = (self._probePos % (2 * math.ceil(math.floor(self._t / 2) / 2))) + 2


class SearchLightRandomNode(SearchLightNode):
    def __init__(self, slotOffset = 0, dutycycle = 0.05, alignmentOffset = 0, name = 'A', otherNode = None):
        super().__init__(slotOffset, dutycycle, alignmentOffset, name, otherNode)
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
        else:
            self._index = 0
            random.shuffle(self._numbers)
        self._probePos = self._numbers[self._index]

class SearchLightStripedRandomNode(SearchLightNode):
    def __init__(self, slotOffset = 0, dutycycle = 0.05, alignmentOffset = 0, name = 'A', otherNode = None):
        super().__init__(slotOffset, dutycycle, alignmentOffset, name, otherNode)
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
        else:
            self._index = 0
            random.shuffle(self._numbers)
        self._probePos = self._numbers[self._index]
