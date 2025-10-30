from itertools import accumulate
import math
import random
import simpy
import os
from typing import List
from typing import TypedDict
from operator import attrgetter
from multiprocessing import Pool
from algos.node import NodeFactory, Node


def convertToCDF(inputList: List[int], n):
    cum = list(accumulate(inputList))
    cdf = list(map(lambda x: x / n, cum))

    return cdf


class Algo(TypedDict):
    nodeType: NodeFactory
    name: str


class SimResults(TypedDict):
    id: int
    latency: int
    unilateralDiscoveries: List[int]
    accumDiscoveries: List[int]
    collisions: int


class SimEnvironment:
    def __init__(self, name: str, N: int, nodeFactory: NodeFactory) -> None:
        self._name = name
        self._results: SimResults = {
            "id": 0,
            "latency": 0,
            "finalDC": 0,
            "collisions": 0,
            "unilateraldiscoveries": [],
            "accumDiscoveries": [],
            "accumCollisions": [],
            "DCAvg": [],
        }
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

            if self._env.now > self._startTime:

                done = True
                for node in self._nodes:
                    if node.id != msg["from"] and node.listening:
                        self._env.process(node.receiveMessage(msg))
                    if not node.neighborsDiscovered == self._N:
                        done = False

                if done:
                    break

    def run(self, maxTime):

        lastNode = max(self._nodes, key=attrgetter('slotOffset'))
        if "Reward" in self._nodeFactory.nodeTypeName:
            self._startTime = lastNode.slotOffset + lastNode.alignmentOffset + 200 * random.random()
            for node in self._nodes:
                node.setSimStartTime(self._startTime)
        else:
            self._startTime = lastNode.slotOffset + lastNode.alignmentOffset + lastNode.T * random.random()
        # self._startTime = 95.31705676235585
        # print("starting time", self._startTime)

        self._env.process(self.routeMessages())
        for node in self._nodes:
            self._env.process(node.run(maxTime+self._startTime))

        # print("simtime", maxTime+self._startTime)
        self._env.run(until=maxTime+self._startTime)

        latencies = [(node.latency - self._startTime) for node in self._nodes]
        latencies.sort()
        latency = math.ceil(min(latencies[-2], maxTime-1))

        collisions_per_node = [(node.collisions) for node in self._nodes]

        discoveries = [0] * maxTime
        for node in self._nodes:
            for el in node.discoveredTimes:
                try:
                    discoveries[math.ceil(el - self._startTime)] += 1
                except IndexError:
                    print("INDEX ERROR", el-self._startTime)

        accumDiscoveries = list(accumulate(discoveries))

        colls = [0] * maxTime
        for node in self._nodes:
            for el in node.collisionTimes:
                try:
                    colls[math.ceil(el - self._startTime)] += 1
                except IndexError:
                    continue
                    # print("INDEX ERROR COlls", el-self._startTime)

        accumColls = list(accumulate(colls))

        DCAvg = [0] * maxTime
        finalDC_per_node = [0]
        if "Reward" in self._nodeFactory.nodeTypeName:
            for node in self._nodes:
                updates = [(round(t - self._startTime), v) for t, v in node.DCUpdates]
                # print(updates[0])
                # print(node.DCUpdates[0])
                for i in range(maxTime):
                    if not updates:
                        break
                    if len(updates) > 1 and i >= updates[1][0]:
                        updates = updates[1:]
                    if not updates:
                        break
                    if updates[0][0] >= 0:
                        DCAvg[i] += updates[0][1] / len(self._nodes)

            finalDC_per_node = [(node.finalDC) for node in self._nodes]

        self._results["finalDC"] = sum(finalDC_per_node) / self._N
        self._results["collisions"] = sum(collisions_per_node) / self._N
        self._results["accumDiscoveries"] = accumDiscoveries
        self._results["accumCollisions"] = accumColls
        self._results["DCAvg"] = DCAvg


        # if latency > maxTime-2:
        #     absOffset = min(lastNode.alignmentOffset, math.fabs(1 - lastNode.alignmentOffset))
        #     m = lastNode.m
        #     T = lastNode.T
        #     slotOffset = lastNode.slotOffset
        #     alignmentOffset = lastNode.alignmentOffset
        #     alpha = lastNode.alpha

        #     if slotOffset <= math.ceil(m / 2) - 1 and alignmentOffset > 1-alpha:
        #         print("Correcto 1")
        #     elif slotOffset == math.ceil(m / 2) and alignmentOffset < alpha:
        #         print("Correcto 2")
        #     elif slotOffset >= T - (math.ceil(m / 2) - 1) and alignmentOffset < alpha:
        #         print("Correcto 3")
        #     elif slotOffset == T - (math.ceil(m / 2)) and alignmentOffset < alpha:
        #         print("Correcto 4")
        #     elif absOffset < lastNode.alpha:
        #         print(f"Correcto, {self._startTime}, so: {lastNode.slotOffset}, \tao: {lastNode.alignmentOffset}, \tdiff: {absOffset}")
        #     else:
        #         print(f"Fallo, {self._startTime}, \tso: {lastNode.slotOffset}, \tao: {lastNode.alignmentOffset}, \tdiff: {absOffset}")

        return self._results


class Test:
    def __init__(self, algorithms: List[Algo],  numTests=1000, maxTime=2000, numNodes=10) -> None:
        self.numTests = numTests
        self.timeToFinishResults = {}
        self.discoveryProportionResults = {}
        self.collisionResults = {}
        self.DCAvgResults = {}
        self.maxTime = maxTime
        self.numNodes = numNodes
        self.algorithms = algorithms

    def runSingleTest(self, algorithm):
        environment = SimEnvironment("", N=self.numNodes, nodeFactory=algorithm["nodeType"])
        results = environment.run(self.maxTime)
        # print("HOLA")
        # print(results)
        return results

    def writeResultToFile(self, filename, result, xLabel: str, xLength: int):
        with open(filename, 'w') as file:
            keys = [xLabel] + list(result.keys())

            line = ''
            for key in keys:
                line += key + '\t'
            print(line.strip(), file=file)

            for i in range(xLength):
                line = ''
                for key in keys:
                    if key == xLabel:
                        line += f'{i}\t'
                    else:
                        line += f'{result[key][i]}\t'
                print(line.strip(), file=file)

    def run(self):
        for algorithm in self.algorithms:
            timeToFinish = [0] * self.maxTime
            accumDiscoveries = [0] * self.maxTime
            accumCollisions = [0] * self.maxTime
            DCAvg = [0] * self.maxTime
            collisions = 0
            finalDC = 0
            # print(algorithm["name"])
            with Pool(os.cpu_count()) as p:
                print("HOLA")
                jobOutput = p.map(self.runSingleTest, [algorithm] * self.numTests)
                for el in jobOutput:
                    timeToFinish[el["latency"]] += 1
                    collisions += el["collisions"] / self.numTests
                    finalDC += el["finalDC"] / self.numTests
                    for i, v in enumerate(el["accumDiscoveries"]):
                        accumDiscoveries[i] += v
                    for i, v in enumerate(el["accumCollisions"]):
                        accumCollisions[i] += v
                    for i, v in enumerate(el["DCAvg"]):
                        DCAvg[i] += v / self.numTests
                # print(f"AVG COLLISIONS per node per test: {collisions / self.numTests}")

            self.timeToFinishResults[algorithm["name"]] = convertToCDF(timeToFinish, self.numTests)
            self.discoveryProportionResults[algorithm["name"]] = list(map(lambda x: x / (self.numTests * self.numNodes * (self.numNodes - 1)), accumDiscoveries))
            self.collisionResults[algorithm["name"]] = accumCollisions
            if "Reward" in algorithm["name"]:
                self.DCAvgResults[algorithm["name"]] = DCAvg
            print("ACCUMDISCOVERIES", accumDiscoveries[-1])
            print("COLLISIONS", algorithm["name"], collisions)
            print("FINALDC", algorithm["name"], finalDC)

        self.writeResultToFile(f'time-to-finish-{self.numNodes}-nodes.tsv', self.timeToFinishResults, "time_to_finish", self.maxTime)
        self.writeResultToFile(f'discoveryProportion-{self.numNodes}-nodes.tsv', self.discoveryProportionResults, "discovery_proportion", self.maxTime)
        self.writeResultToFile(f'collisions-{self.numNodes}-nodes.tsv', self.collisionResults, "collisions", self.maxTime)
        self.writeResultToFile(f'DC-{self.numNodes}-nodes.tsv', self.DCAvgResults, "DC-avg", self.maxTime)
