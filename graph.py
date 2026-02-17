from algos.algos import Test
from algos.fedab import FedabNodeFactory, FedabStochasticNodeFactory
from algos.reward import RewardNodeFactory, Reward2NodeFactory, Reward3NodeFactory, Reward4NodeFactory, RewardStaticNodeFactory
import sys

# maxTime = 2500
# maxTime = 5000
# maxTime = 25_000
# maxTime = 700
maxTime = 50_000

numNodes = int(sys.argv[1])
dc = int(sys.argv[2]) / 100
trials = int(sys.argv[3])
T = 100
alpha = 0.125
print(numNodes, dc, trials)
test = Test([
    {
        "name": f"Static @{round(dc, 2)}-dc-{numNodes}-nodes",
        "nodeType": RewardStaticNodeFactory(startDC=dc, alpha=alpha)
    },

], name=f"{numNodes}-nodes-{dc}-dc-{T}-T-{alpha}-alpha", numTests=trials, maxTime=maxTime, numNodes=numNodes)


results = test.run()
