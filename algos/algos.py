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
            "avgCollisions": 0,
            "avgCleanDiscoveries": 0,
            "avgEmtySlots": 0,
            "latencies": defaultdict(int),
            "unilateraldiscoveries": [],
            "accumDiscoveries": [],
            "accumCollisions": [],

            "history": [],
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


        firstNode = min(self._nodes, key=attrgetter('slotOffset'))
        lastNode = max(self._nodes, key=attrgetter('slotOffset'))
        # if "Reward" in self._nodeFactory.nodeTypeName:
        #     self._startTime = lastNode.slotOffset + lastNode.alignmentOffset + 100 * random.random()
        #     for node in self._nodes:
        #         node.setSimStartTime(self._startTime)
        # else:
        #     self._startTime = lastNode.slotOffset + lastNode.alignmentOffset + lastNode.T * random.random()
        self._startTime = 100
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

        colls_per_node = [(node.collisions) for node in self._nodes]
        avg_colls = sum(colls_per_node) / len(colls_per_node) if colls_per_node else 0

        clean_per_node = [(node.cleanDiscoveries) for node in self._nodes]
        avg_clean = sum(clean_per_node) / len(clean_per_node) if clean_per_node else 0

        empties_per_node = [(node.emptySlots) for node in self._nodes]
        avg_empties = sum(empties_per_node) / len(empties_per_node) if empties_per_node else 0

        finalDC_per_node = [(node.finalDC) for node in self._nodes]

        self._results["finalDC"] = sum(finalDC_per_node) / self._N
        self._results["avgCollisions"] = avg_colls
        self._results["avgCleanDiscoveries"] = avg_clean
        self._results["avgEmptySlots"] = avg_empties

        # self._results["collisions"] = 100 * sum(collisions_per_node) / (self._N * (self._stopTime - self._startTime))
        # self._results["accumDiscoveries"] = accumDiscoveries
        # self._results["accumCollisions"] = accumColls
        # self._results["DCAvg"] = DCAvg

        self._results["history"] = [(i, x, y) for node in self._nodes for i, (x, y) in enumerate(zip(node._collisionMem, node._cleanDiscoveryMem), start=1)]



        self._results["latency"] = latency
        self._results["first-node-latency"] = firstNode.latency - self._startTime
        for latency in latencies:
            self._results["latencies"][latency] += 1

        return self._results


class Test:
    def __init__(self, algorithms: List[Algo],  name="test", numTests=1000, maxTime=2000, numNodes=10) -> None:
        self.numTests = numTests
        self.latencyCDF = {}
        self.firstNodeLatencyDist = {}
        self.latencyDist = {}
        self.finalDC = {}
        self.avgCollisions = {}
        self.avgCleanDiscoveries = {}
        self.avgEmptySlots = {}
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


    def writeSingleDatapoint(self, datapoint, label):
        print(f'{label}: {datapoint}')
        os.makedirs(f"./exp-data/{self.name}", exist_ok=True)
        with open(f'./exp-data/{self.name}/{self.numNodes}-nodes-{label}.tsv', 'w') as f:
            headers = datapoint.keys()
            writer = csv.DictWriter(f, fieldnames=headers, delimiter='\t')
            writer.writeheader()
            writer.writerow(datapoint)

    def appendDatapoint(self, datapoint, label):
        os.makedirs(f"./exp-data/{self.name}", exist_ok=True)
        with open(f'./exp-data/{self.name}/{self.numNodes}-nodes-{label}.data', 'a') as f:
            f.write(','.join(str(n) for n in datapoint) + '\n')

    def run(self):

        print('start test run')
        for algorithm in self.algorithms:
            # latencyDist = [0] * self.maxTime
            firstNodeLatencyDist = defaultdict(int)
            latencyDist = defaultdict(int)
            # accumDiscoveries = [0] * self.maxTime
            avgCollisions = 0
            avgCleanDiscoveries = 0
            avgEmptySlots = 0
            finalDC = 0

            with Pool(max(1, os.cpu_count()-1)) as p:
                jobOutput = p.map(self.runSingleTest, [algorithm] * self.numTests)
                for el in jobOutput:
                    # latencyDist[el["latency"]] += 1
                    firstNodeLatencyDist[min(el["first-node-latency"], self.maxTime-1)] += 1
                    for slot, freq in el["latencies"].items():
                        latencyDist[slot] += freq
                    # collisions += el["collisions"] / self.numTests
                    avgCollisions = el["avgCollisions"] / self.numTests
                    avgCleanDiscoveries = el["avgCleanDiscoveries"] / self.numTests
                    avgEmptySlots = el["avgEmptySlots"] / self.numTests
                    finalDC += el["finalDC"] / self.numTests
                    for i, v in enumerate(el["accumDiscoveries"]):
                        accumDiscoveries[i] += v
                    for i, v in enumerate(el["accumCollisions"]):
                        accumCollisions[i] += v
                    for i, v in enumerate(el["DCAvg"]):
                        DCAvg[i] += v / self.numTests


                    for datapoint in el["history"]:
                        self.appendDatapoint(datapoint, 'history')


            # self.latencyCDF[algorithm["name"]] = getCDF(latencyDist, self.numTests)

            self.finalDC[algorithm["name"]] = finalDC
            self.avgCollisions[algorithm["name"]] = avgCollisions
            self.avgCleanDiscoveries[algorithm["name"]] = avgCleanDiscoveries
            self.avgEmptySlots[algorithm["name"]] = avgEmptySlots

            self.firstNodeLatencyDist[algorithm["name"]] = firstNodeLatencyDist
            self.latencyDist[algorithm["name"]] = latencyDist

            self.writeSingleDatapoint(self.finalDC, 'final-dc')

            self.writeSingleDatapoint(self.avgCollisions, 'avg-collisions')
            self.writeSingleDatapoint(self.avgCleanDiscoveries, 'avg-clean-discoveries')
            self.writeSingleDatapoint(self.avgEmptySlots, 'avg-empty-slots')

            # self.discoveryProportionResults[algorithm["name"]] = list(map(lambda x: x / (self.numTests * self.numNodes * (self.numNodes - 1)), accumDiscoveries))
            # self.collisionResults[algorithm["name"]] = accumCollisions
            # if "Reward" in algorithm["name"]:
            #     self.DCAvgResults[algorithm["name"]] = DCAvg
            # print("ACCUMDISCOVERIES", accumDiscoveries[-1])
            # print("COLLISIONS", algorithm["name"], collisions)
            # print("FINALDC", algorithm["name"], finalDC)

        # self.writeResultToFile(f'./discovery-data/{self.name}-latency-cdf.tsv', self.latencyCDF, "time_to_finish", self.maxTime)
        self.writeResultToFile(f'./exp-data/{self.name}/{self.numNodes}-nodes-first-node-latency.tsv', self.firstNodeLatencyDist, "first-node-latency", self.maxTime)
        self.writeResultToFile(f'./exp-data/{self.name}/{self.numNodes}-nodes-latencies.tsv', self.latencyDist, "latency", self.maxTime)
        # self.writeResultToFile(f'./discovery-data/{self.name}-discoveryProportion-{self.numNodes}-nodes.tsv', self.discoveryProportionResults, "discovery_proportion", self.maxTime)
        # self.writeResultToFile(f'./discovery-data/{self.name}-collisions.tsv', self.collisionResults, "collisions", self.maxTime)
        # self.writeResultToFile(f'./discovery-data/{self.name}-DC-{self.numNodes}-nodes.tsv', self.DCAvgResults, "DC-avg", self.maxTime)
