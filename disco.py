# import sympy as sp
# import math
from functools import reduce
from itertools import accumulate
import random

max_iterations = 5000

class Disco:
    def __init__(self, nodes) -> None:
        self.nodes = nodes

    def getLatency(self) -> int:
        count = 0
        found = False
        while not found and count < max_iterations - 1:
            found = True
            for node in self.nodes:
                turnedOn = False
                for prime in node.getPrimes():
                    if (count - node.getOffset()) % prime == 0:
                        turnedOn = True
                        break
                if not turnedOn:
                    found = False
                    break

            count += 1

        return count

class DiscoNode:

    def __init__(self, primes = (), offset = 0, dutycycle = 0.05) -> None:
        self.nodeClass = 0
        self.primes = primes
        if not self.primes:
            self.setDutyCycle(dutycycle)
        if not offset:
            self.offset = random.randint(0, reduce(lambda x, y: x * y, self.primes))

    def setDutyCycle(self, dutycycle = 0.05) -> None:
        possiblePrimes = [(23, 157), (29, 67), (31, 59), (37, 43)]
        self.primes = random.choice(possiblePrimes)

    def getDutyCycle(self) -> float:
        return reduce(lambda x, y: x + 1 / y, self.primes, 0)

    def getPrimes(self):
        return self.primes

    def getOffset(self) -> int:
        return self.offset

    def setNodeClass(self, classId: int) -> None:
        self.classId = classId

    def getNodeClass(self) -> int:
        return self.nodeClass

    def setBeaconMode(self, beacon: bool) -> None:
        self.beacon = beacon

    def getBeaconMode(self) -> bool:
        return self.beacon

class Test:
    def __init__(self, primePairs, numTests = 1000) -> None:
        self.primePairs = primePairs
        self.numTests = numTests
        self.testResults = {}

    def run(self):
        for pair in self.primePairs:
            discoveries = [0] * max_iterations
            for _ in range(self.numTests):
                disco = Disco([DiscoNode(pair[0]), DiscoNode(pair[1])])
                discoveries[disco.getLatency()] += 1

            acummDiscoveries = list(accumulate(discoveries))

            cdf = list(map(lambda x: x / self.numTests, acummDiscoveries))
            self.testResults[str(pair)] = cdf


        return self.testResults

# test = Test([ ((37, 43), (37, 43)) ])

test = Test([ ((37, 43), (37, 43)),
              ((23, 157), (29, 67)),
              ((23, 157), (23, 157)),
            ])

# test = Test([ ((61, 73), (61, 73)),
#               ((97, 103), (47, 53)),
#               ((191, 211), (37, 43)),
#             ])

results = test.run()

keys = ['slot'] + list(results.keys())

line = ''
for key in keys:
    line += key + '\t'
print(line.strip())

for i in range(max_iterations):
    line = ''
    for key in keys:
        if key == 'slot':
            line += f'{i}\t'
        else:
            line += f'{results[key][i]}\t'
    print(line.strip())
