from functools import reduce
from itertools import accumulate
import math
import random
import simpy
import simpy.core
import simpy.util

class Algorithm:
    def __init__(self, nodeA, nodeB, name) -> None:
        self._nodeA = nodeA
        self._nodeB = nodeB
        self._name = name

    def getName(self) -> str:
        return self._name

    def getLatency(self, maxTime):
        self._nodeA.restart()
        self._nodeB.restart(self._nodeA)

        offset = self._nodeB.getSlotOffset()

        env = simpy.Environment()
        pipeA = []
        pipeB = []

        env.process(self._nodeA.run(env, pipeA, pipeB))
        env.process(self._nodeB.run(env, pipeB, pipeA))

        # alignmentOffset = self._nodeB.getAlignment()
        # simpy.util.start_delayed(env, self._nodeB.run(env, pipeB, pipeA), offset + alignmentOffset)

        env.run(until=maxTime+offset)

        return math.ceil(min(self._nodeB.latency, maxTime-1))


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
