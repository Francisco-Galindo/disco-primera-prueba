from itertools import accumulate
import math
import random
import simpy
import os
import csv
from typing import List
from typing import TypedDict
from operator import attrgetter
from multiprocessing import Pool
from algos.node import NodeFactory, Node
from collections import defaultdict


def getCDF(inputList: List[int], n):
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
            "latencies": defaultdict(int),
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
        self._stopTime = 0

        for i in range(N):
            newNode = nodeFactory.produce(self._env, self._mesgPipe, id=i, numNeighbors=self._N-1)
            self._nodes.append(newNode)
        # newNode = nodeFactory.produce(self._env, self._mesgPipe, id=0, numNeighbors=self._N-1, slotOffset=0, alignmentOffset=0)
        # newNode = nodeFactory.produce(self._env, self._mesgPipe, id=1, numNeighbors=self._N-1, slotOffset=10, alignmentOffset=0.5)
        # newNode = nodeFactory.produce(self._env, self._mesgPipe, id=2, numNeighbors=self._N-1, slotOffset=10, alignmentOffset=0.5)
        # self._nodes.append(newNode)

    def getName(self) -> str:
        return self._name

    def stopAll(self, time):
        self._stopTime = time
        for node in self._nodes:
            node.stop()

    def routeMessages(self):
        """Distribute a message sent by a node into all other nodes."""
        while True:
            # wait for next msg and get it
            msg = yield self._mesgPipe.get()

            if self._env.now > self._startTime:

                done = True
                for node in self._nodes:
                    # if node.id != msg["from"] and node.listening:
                    if node.id != msg["from"]:
                        self._env.process(node.receiveMessage(msg))
                    if not node.neighborsDiscovered == self._N - 1:
                        done = False

                if done:
                    self.stopAll(self._env.now)
                    break

    def run(self, maxTime):

        # print('hola2')
        firstNode = min(self._nodes, key=attrgetter('slotOffset'))
        lastNode = max(self._nodes, key=attrgetter('slotOffset'))
        # if "Reward" in self._nodeFactory.nodeTypeName:
        #     self._startTime = lastNode.slotOffset + lastNode.alignmentOffset + 100 * random.random()
        #     for node in self._nodes:
        #         node.setSimStartTime(self._startTime)
        # else:
        #     self._startTime = lastNode.slotOffset + lastNode.alignmentOffset + lastNode.T * random.random()
        self._startTime = 100
        # self._startTime = 95.31705676235585
        # print("starting time", self._startTime)

        self._env.process(self.routeMessages())
        for node in self._nodes:
            self._env.process(node.run(maxTime+self._startTime))

        self._stopTime = maxTime
        self._env.run(until=maxTime+self._startTime)

        latencies = [(node.latency - self._startTime) for node in self._nodes]
        # latency = math.ceil(min(max(latencies), maxTime-1))
        # MEMORY OPTIMIZATION:
        # Use a generator expression inside max() to avoid creating a new list.
        # We find the raw max latency first, then subtract startTime once.
        max_raw_latency = max(node.latency for node in self._nodes)

        # Calculate final latency
        adjusted_latency = max_raw_latency - self._startTime
        latency = math.ceil(min(adjusted_latency, maxTime - 1))

        # collisions_per_node = [(node.collisions) for node in self._nodes]

        # discoveries = [0] * maxTime
        # for node in self._nodes:
        #     for el in node.discoveredTimes:
        #         try:
        #             discoveries[math.ceil(el - self._startTime)] += 1
        #         except IndexError:
        #             print("INDEX ERROR", el-self._startTime)

        # accumDiscoveries = list(accumulate(discoveries))

        # colls = [0] * maxTime
        # for node in self._nodes:
        #     for el in node.collisionTimes:
        #         try:
        #             colls[math.ceil(el - self._startTime)] += 1
        #         except IndexError:
        #             continue
        #             # print("INDEX ERROR COlls", el-self._startTime)

        # accumColls = list(accumulate(colls))

        # DCAvg = [0] * maxTime
        # finalDC_per_node = [0]
        # if "Reward" in self._nodeFactory.nodeTypeName:
        #     for node in self._nodes:
        #         updates = [(round(t - self._startTime), v) for t, v in node.DCUpdates]
        #         # print(updates[0])
        #         # print(node.DCUpdates[0])
        #         for i in range(maxTime):
        #             if not updates:
        #                 break
        #             if len(updates) > 1 and i >= updates[1][0]:
        #                 updates = updates[1:]
        #             if not updates:
        #                 break
        #             if updates[0][0] >= 0:
        #                 DCAvg[i] += updates[0][1] / len(self._nodes)

        finalDC_per_node = [(node.finalDC) for node in self._nodes]

        self._results["finalDC"] = sum(finalDC_per_node) / self._N
        # self._results["collisions"] = 100 * sum(collisions_per_node) / (self._N * (self._stopTime - self._startTime))
        # self._results["accumDiscoveries"] = accumDiscoveries
        # self._results["accumCollisions"] = accumColls
        # self._results["DCAvg"] = DCAvg
        self._results["latency"] = latency
        self._results["first-node-latency"] = firstNode.latency
        for latency in latencies:
            self._results["latencies"][latency] += 1
        # print('a')

        return self._results


class Test:
    def __init__(self, algorithms: List[Algo],  name="test", numTests=1000, maxTime=2000, numNodes=10) -> None:
        self.numTests = numTests
        self.latencyCDF = {}
        self.firstNodeLatencyDist = {}
        self.latencyDist = {}
        self.finalDC = {}
        self.discoveryProportionResults = {}
        self.collisionResults = {}
        self.DCAvgResults = {}
        self.maxTime = maxTime
        self.numNodes = numNodes
        self.algorithms = algorithms
        self.name = name

    def runSingleTest(self, algorithm):
        environment = SimEnvironment("", N=self.numNodes, nodeFactory=algorithm["nodeType"])
        results = environment.run(self.maxTime)
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

    def get_cpus():
        slurm_cpus = os.environ.get('SLURM_CPUS_PER_TASK')

        if slurm_cpus:
            return int(slurm_cpus)

        # Fallback for local testing (not on a cluster)
        return max(1, os.cpu_count()-1)

    def run(self):

        print('start test run')
        for algorithm in self.algorithms:
            # latencyDist = [0] * self.maxTime
            firstNodeLatencyDist = defaultdict(int)
            latencyDist = defaultdict(int)
            # accumDiscoveries = [0] * self.maxTime
            collisions = 0
            finalDC = 0
            algorithm

            with Pool(max(1, os.cpu_count()-1)) as p:
                jobOutput = p.map(self.runSingleTest, [algorithm] * self.numTests)
                for el in jobOutput:
                    # latencyDist[el["latency"]] += 1
                    firstNodeLatencyDist[min(el["first-node-latency"], self.maxTime-1)] += 1
                    for slot, freq in el["latencies"].items():
                        latencyDist[slot] += freq
                    # collisions += el["collisions"] / self.numTests
                    finalDC += el["finalDC"] / self.numTests
                    for i, v in enumerate(el["accumDiscoveries"]):
                        accumDiscoveries[i] += v
                    for i, v in enumerate(el["accumCollisions"]):
                        accumCollisions[i] += v
                    for i, v in enumerate(el["DCAvg"]):
                        DCAvg[i] += v / self.numTests

            # self.latencyCDF[algorithm["name"]] = getCDF(latencyDist, self.numTests)
            self.finalDC[algorithm["name"]] = finalDC
            self.firstNodeLatencyDist[algorithm["name"]] = firstNodeLatencyDist
            self.latencyDist[algorithm["name"]] = latencyDist
            # self.discoveryProportionResults[algorithm["name"]] = list(map(lambda x: x / (self.numTests * self.numNodes * (self.numNodes - 1)), accumDiscoveries))
            # self.collisionResults[algorithm["name"]] = accumCollisions
            # if "Reward" in algorithm["name"]:
            #     self.DCAvgResults[algorithm["name"]] = DCAvg
            # print("ACCUMDISCOVERIES", accumDiscoveries[-1])
            # print("COLLISIONS", algorithm["name"], collisions)
            # print("FINALDC", algorithm["name"], finalDC)

        # self.writeResultToFile(f'./discovery-data/{self.name}-latency-cdf.tsv', self.latencyCDF, "time_to_finish", self.maxTime)
        print(self.finalDC)
        os.makedirs(f"./exp-data/{self.name}", exist_ok=True)
        with open(f'./exp-data/{self.name}/{self.numNodes}-nodes-final-dc.tsv', 'w') as f:
            headers = self.finalDC.keys()
            writer = csv.DictWriter(f, fieldnames=headers, delimiter='\t')
            writer.writeheader()
            writer.writerow(self.finalDC)
        self.writeResultToFile(f'./exp-data/{self.name}/{self.numNodes}-nodes-first-node-latency.tsv', self.firstNodeLatencyDist, "first-node-latency", self.maxTime)
        self.writeResultToFile(f'./exp-data/{self.name}/{self.numNodes}-nodes-latencies.tsv', self.latencyDist, "latency", self.maxTime)
        # self.writeResultToFile(f'./discovery-data/{self.name}-discoveryProportion-{self.numNodes}-nodes.tsv', self.discoveryProportionResults, "discovery_proportion", self.maxTime)
        # self.writeResultToFile(f'./discovery-data/{self.name}-collisions.tsv', self.collisionResults, "collisions", self.maxTime)
        # self.writeResultToFile(f'./discovery-data/{self.name}-DC-{self.numNodes}-nodes.tsv', self.DCAvgResults, "DC-avg", self.maxTime)
