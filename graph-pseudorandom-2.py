from algos.algos import Test
from algos.reward import LCGNode2Factory
import sys


def harmonic(n):
    s = 0
    for i in range(1, n+1):
        s += 1 / i

    return s


numNodes = int(sys.argv[1])
dc = int(sys.argv[2]) / 100
trials = int(sys.argv[3])

T = 100
alpha = 2**-5
print(numNodes, dc, trials)

L = 1
n = numNodes
numerator = T * harmonic(n-1)
DC = int(dc * 100)
p_succ_1 = ((2 * DC**2 * (L - 3 * alpha)) / T) * (1 - (4 * DC * alpha)/T)**(n-2)
expectedTime = numerator / p_succ_1
maxTime = min(1_000_000, int(expectedTime * 100))
print('maxtime', maxTime)

test = Test([
    {
        "name": f"{numNodes}-nodes",
        "nodeType": LCGNode2Factory(startDC=dc, alpha=alpha)
    },

], name=f"LCG2-{dc}-dc-{alpha}-alpha", numTests=trials, maxTime=maxTime, numNodes=numNodes)


results = test.run()
