from itertools import accumulate
import math
import random
import simpy
from typing import List
from typing import TypedDict
from operator import attrgetter
from algos.node import NodeFactory, Node


class Algo(TypedDict):
    nodeType: NodeFactory
    name: str


class SimResults(TypedDict):
    id: int
    latency: int
    unilateralDiscoveriesMass: List[int]
    collisions: int


class SimEnvironment:
    def __init__(self, name: str, N: int, nodeFactory: NodeFactory) -> None:
        self._name = name
        self._results: SimResults = {"id": 0, "latency": 0, "collisions": 0, "unilateraldiscoveries": []}
        self._env = simpy.Environment()
        self._mesgPipe = simpy.Store(self._env)
        self._nodes: List[Node] = []
        self._nodeFactory = nodeFactory
        self._N = N
        self._startTime = 0

        for i in range(N):
            newNode = nodeFactory.produce(self._env, self._mesgPipe, id=i, numNeighbors=self._N-1)
            self._nodes.append(newNode)

    def getName(self) -> str:
        return self._name

    def routeMessages(self):
        """Distribute a message sent by a node into all other nodes."""
        while True:
            # wait for next msg and get it
            msg = yield self._mesgPipe.get()
            # print("GOT MESSAGE")

            if self._env.now > self._startTime:

                done = True
                for node in self._nodes:
                    if node.id != msg["from"] and node.listening:
                        # print("HOLA from ", msg["from"], self._env.now, msg["now"], self._startTime, node.id)
                        self._env.process(node.receiveMessage(msg))
                    if not node.neighborsDiscovered == self._N:
                        done = False

                if done:
                    break

    def run(self, maxTime):

        lastNode = max(self._nodes, key=attrgetter('slotOffset'))
        # self._startTime = lastNode.slotOffset + lastNode.alignmentOffset + lastNode.T * random.random()
        self._startTime = lastNode.slotOffset + lastNode.alignmentOffset + 2000 * random.random()
        self._startTime = 1.1
        # self._startTime = 112.91033577615596
        # print("starting time", self._startTime)

        self._env.process(self.routeMessages())
        for node in self._nodes:
            self._env.process(node.run(maxTime+self._startTime))

        # print("simtime", maxTime+self._startTime)
        self._env.run(until=maxTime+self._startTime)

        latencies = [(node.latency - self._startTime) for node in self._nodes]
        latency = math.ceil(min(max(latencies), maxTime-1))

        self._results["latency"] = latency
        if latency > maxTime-2:
            print("PEPE", self._startTime, lastNode.slotOffset, lastNode.alignmentOffset, lastNode.T)

        return self._results


class Test:
    def __init__(self, algorithms: List[Algo], numTests = 1000, maxTime = 2000, numNodes = 10) -> None:
        self.numTests = numTests
        self.testResults = {}
        self.maxTime = maxTime
        self.numNodes = numNodes
        self.algorithms = algorithms

    def run(self):
        for algorithm in self.algorithms:
            discoveries = [0] * self.maxTime
            for i in range(self.numTests):
                # print('Test', i)
                environment = SimEnvironment("", N=self.numNodes, nodeFactory=algorithm["nodeType"])
                results = environment.run(self.maxTime)
                latency = results["latency"]
                discoveries[latency] += 1

            accumDiscoveries = list(accumulate(discoveries))

            cdf = list(map(lambda x: x / self.numTests, accumDiscoveries))
            self.testResults[algorithm["name"]] = cdf

        return self.testResults
