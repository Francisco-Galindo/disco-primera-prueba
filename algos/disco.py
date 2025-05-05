from functools import reduce
from itertools import accumulate
import math
import random
import simpy
import simpy.core
import simpy.util

class DiscoNode:

    def __init__(self, primes = (), slotOffset = 0, dutycycle = 0.05, name = 'A', otherNode = None) -> None:
        self.nodeClass = 0
        self._primes = primes
        self._name = name
        if not self._primes:
            self.setDutyCycle(dutycycle)

        self.restart(otherNode)

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


    def restart(self, otherNode = None) -> None:
        self._slotOffset = 0
        self._alignmentOffset = 0

        if self._name == 'B' and otherNode:
            self._slotOffset = random.randint(0, math.floor(reduce(lambda x, y: x * y, otherNode._primes)))
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
