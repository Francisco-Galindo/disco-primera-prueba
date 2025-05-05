from functools import reduce
from itertools import accumulate
import math
import random
import simpy
import simpy.core
import simpy.util

class FedabNode:

    def __init__(self, slotOffset = 0, dutycycle = 0.05, alignmentOffset = 0, alpha = 0.054, name = 'A', otherNode = None) -> None:
        self._name = name
        self._alpha = alpha
        self._m = math.ceil(2 / dutycycle)
        self._n = math.ceil(alpha / dutycycle)

        self._turnedOn = False
        self._slotOffset = slotOffset
        self._alignmentOffset = alignmentOffset
        if not slotOffset:
            self.restart(otherNode)

        self.setDutyCycle(dutycycle)

        self._m = 5
        self._n = 3


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

    def restart(self, otherNode = None) -> None:
        self._alignmentOffset = 0
        self._slotOffset = 0
        self.latency = 1_000_000_000

        if self._name == 'B' and otherNode:
            self._alignmentOffset = random.random()
            # self._slotOffset = random.randint(0, math.ceil(otherNode.getT()))
            self._slotOffset = 0

    def run(self, env, beaconPipe, listenPipe):
        startingTime = self._alignmentOffset + self._slotOffset
        yield env.timeout(startingTime)

        found = False
        activelySearching = False
        whenToBeacon = math.inf
        i = 0
        print('started', self._name, env.now, i, self._m, self._n, self.getT())
        while not found or activelySearching:
            if self._name == 'A':
                print('iter', self._name, env.now, self._m, self._n)
            remainingSlotTime = 1
            if 1 <= i % self.getT() <= math.ceil(self._m / 2) or env.now > whenToBeacon:
                # if env.now > whenToBeacon:
                #     print("ANDORRA")
                remainingSlotTime -= self._alpha

                timeToNextListen = self._m - (i % self._m)
                nextListenAbsTime = env.now + timeToNextListen
                beaconPipe.append((env.now, nextListenAbsTime, activelySearching))
                yield env.timeout(self._alpha)
                if self._name == 'A':
                    print('beaconie', self._name, env.now, nextListenAbsTime)
                beaconPipe.append((env.now, nextListenAbsTime, activelySearching))

            yield env.timeout(remainingSlotTime)

            while i % self._m == 0 and listenPipe and not activelySearching:
                print('hola', i)
                msg = listenPipe.pop()
                if msg[0] >= startingTime and (msg[0] - startingTime) % self._m < 1:
                    print('lol', self._name, env.now, self._m, self._n, msg)
                    found = True
                    activelySearching = True
                    whenToBeacon = msg[1]
                    if msg[2] == True:
                        self.latency = msg[0] - startingTime
                        print("YEA", env.now - startingTime)
                        return

            i += 1
