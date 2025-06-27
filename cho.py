import random
import math
import simpy
import simpy.core
from typing import List
from abc import ABC, abstractmethod

class Node(ABC):
    id: int

    @abstractmethod
    def update(self) -> None:
        pass

    @property
    @abstractmethod
    def transmitting(self) -> bool:
        pass

    @property
    @abstractmethod
    def neighborsDiscovered(self) -> int:
        pass

    @abstractmethod
    def receiveMessage(self, id: int) -> None:
        pass

class NodeFactory(ABC):
    @abstractmethod
    def produce(self, env, slotOffset = 0, alignmentOffset = 0, id = 0) -> Node:
        pass

class ChoNode(Node):
    def __init__(self, env, k, pmax, slotOffset = 0, alignmentOffset = 0, id: int = 0) -> None:
        self.id = id
        self.listening = False
        self.k = k
        self.pmax = pmax
        self.neighbors = []
        self.env = env
        self.t = 1
        self.inPipe = []

        self.N_RX_acum = 0

        self.NDR = 0
        self.E_TX = 0
        self.E_L = 1
        self.T_TX = 0
        self.T_RX = 0
        self.p_G = 0
        self.p_S = 0
        self.p = 0
        self.nHat = 1_000_000
        if random.random() < 0.5:
            self.phase = "slow"
        else:
            self.phase = "greedy"

        # print("INICIANDO", self.id, self.phase)


        self._slotOffset = slotOffset
        self._alignmentOffset = alignmentOffset

    def receiveMessage(self, id: int) -> None:
        if len(self.inPipe) < self.k:
            self.inPipe.append(id)
        else:
            self.inPipe.clear()
        self.N_RX_acum += 1

    def updateParams(self) -> None:
        if self.N_RX_acum > 0 and self.T_TX > 0:
            self.NDR = self.neighborsDiscovered / self.N_RX_acum + 0.000001
            # print('CHECANDO CEROS', self.nHat, "WHAT",  self.NDR, self. T_TX)
            try:
                self.E_TX =  (self.nHat - 1) / ((self.nHat-self.k) * self.NDR * self.T_TX / self.t) - self.T_TX
            except:
                self.E_TX =  100_000
            self.E_L = self.E_TX * self.t / self.T_TX

            self.p_G = min(self.E_TX / (self.E_TX + self.t), self.pmax)
            self.p_S = min((self.T_RX + self.t - 1) / (self.E_L + self.t), self.pmax)
        else:
            self.p_G = self.pmax
            self.p_S = 0.05

        if self.phase == "slow":
            self.p = self.p_S + math.exp(0.001 * self.t) - 1
        elif self.phase == "greedy":
            self.p = self.p_G - (0.001 * self.t)

        if self.N_RX_acum > 0 and self.T_TX > 0:
            self.nHat = self.neighborsDiscovered * (1 / (2 * self.p_G) + 1 / (2 * self.p_G))
        else:
            self.nHat = 1_000_000

        self.t += 1

    @property
    def transmitting(self) -> bool:
        return not self.listening

    def update(self) -> None:
        self.updateParams()

        # Check for RX's on previous slot
        for mesg in self.inPipe:
            if mesg not in self.neighbors:
                # print("HOLA", self.id, mesg)
                self.neighbors.append(mesg)
        self.inPipe.clear()

        # Decide if node is going to RX or TX
        # if self.phase == 'slow':
            # print(self.id, 'P', self.p)
        if random.random() > self.p:
            self.listening = True
            self.T_RX += 1
        else:
            self.listening = False
            self.T_TX += 1
            # print("Transmitting", self.id)


    @property
    def neighborsDiscovered(self) -> int:
        return len(self.neighbors)

class AdaptiveAlohaNode(Node):
    def __init__(self, env, k, pmax, slotOffset = 0, alignmentOffset = 0, id: int = 0) -> None:
        self.id = id
        self.listening = False
        self.k = k
        self.neighbors = []
        self.env = env
        self.simT = 0
        self.inPipe = []
        self.i = 0
        self.n = 1
        self.successfulTxsInPhase = 0
        self.p = 0
        self.W_i = 0
        self.phaseCnt = 0
        self.didDeterministicTX = False

        self._slotOffset = slotOffset
        self._alignmentOffset = alignmentOffset

    def receiveMessage(self, id: int) -> None:
        if len(self.inPipe) < self.k:
            self.inPipe.append(id)
        else:
            self.inPipe.clear()

    def updateParams(self) -> None:
        self.i += 1

        d1 = 100
        self.W_i = d1 * (2**self.i) * math.log(2**self.i) / self.k
        self.p = self.k / (2 ** self.i)
        print("updated", self.id, self.p)

    @property
    def t(self) -> int:
        return self.simT // 2

    @property
    def transmitting(self) -> bool:
        return not self.listening

    def update(self) -> None:

        if self.simT % 2 == 0:
            if self.phaseCnt >= self.W_i:
                self.updateParams()

        # Listen on whole slot if listening, or listen in half slot if transmitting
        if (self.simT % 2 == 1 and self.listening) or (self.simT % 2 == 0 and self.transmitting and not self.didDeterministicTX):
            # Check for RX's on previous slot
            for mesg in self.inPipe:
                if mesg not in self.neighbors:
                    self.neighbors.append(mesg)
                    self.listening = False
                    print(self.id, "Doing deterministic TX")
                    self.didDeterministicTX = True
            self.inPipe.clear()


        if self.simT % 2 == 0:
            self.didDeterministicTX = False
            self.listening = True
            if random.random() < self.p:
                print(self.id, "Doing random TX")
                self.listening = False

            self.phaseCnt += 1

        self.simT += 1


    @property
    def neighborsDiscovered(self) -> int:
        return len(self.neighbors)

class ChoNodeFactory(NodeFactory):
    def __init__(self, k: int, pmax: float) -> None:
        self.k = k
        self.pmax = pmax

    def produce(self, env, slotOffset = 0, alignmentOffset = 0, id: int = 0) -> Node:
        return ChoNode(env, self.k, self.pmax, slotOffset, alignmentOffset, id)

class AdaptiveAlohaNodeFactory(NodeFactory):
    def __init__(self, k: int) -> None:
        self.k = k

    def produce(self, env, slotOffset = 0, alignmentOffset = 0, id: int = 0) -> Node:
        return AdaptiveAlohaNode(env, self.k, slotOffset, alignmentOffset, id)

class Algorithm:
    def __init__(self, N: int, k: int, nodeFactory: NodeFactory, maxTime=10_000) -> None:
        self.N = N
        self.k = k
        self.nodes: List[Node] = []
        self.env = simpy.Environment()
        self.nodeFactory = nodeFactory

        for i in range(N):
            newNode = nodeFactory.produce(self.env, slotOffset=0, alignmentOffset=0, id=i)
            self.nodes.append(newNode)

        self.env.process(self.run())
        self.env.run(until=maxTime)


    @property
    def NDCR(self) -> float:
        sum = 0
        for node in self.nodes:
            sum += node.neighborsDiscovered

        return sum  / (self.N*(self.N-1))

    def run(self):
        i = 0
        while True:
            random.shuffle(self.nodes)

            for node in self.nodes:
                node.update()

                if node.transmitting:
                    for otherNode in self.nodes:
                        if not otherNode.transmitting:
                            otherNode.receiveMessage(node.id)

            yield self.env.timeout(1)

            print("- ROUND: ", i, self.NDCR)
            if self.NDCR >= 0.95:
                break
            i += 1


k = 2
# factory = ChoNodeFactory(k, pmax=0.25)
factory = AdaptiveAlohaNodeFactory(k)
algo = Algorithm(N=4, k=k, nodeFactory=factory)
