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
print(numNodes, dc)
test = Test([
    # {
    #     "name": "Fedab",
    #     "nodeType": FedabNodeFactory(dutyCycle=0.05)
    # },
    # {
    #     "name": "FedabStoc",
    #     "nodeType": FedabStochasticNodeFactory(dutyCycle=0.05)
    # },
    # {
    #     "name": "Reward",
    #     "nodeType": RewardNodeFactory(startDC=0.03)
    # },
    # {
    #     "name": "Reward2",
    #     "nodeType": Reward2NodeFactory(startDC=0.02)
    # },
    # {
    #     "name": "Reward3",
    #     "nodeType": Reward3NodeFactory(startDC=0.02)
    # },
    # {
    #     "name": "Reward4",
    #     "nodeType": Reward4NodeFactory(startDC=0.02)
    # },

    # {
    #     "name": "Static @0.01",
    #     "nodeType": RewardStaticNodeFactory(startDC=0.01)
    # },
    {
        "name": "Static @0.05",
        "nodeType": RewardStaticNodeFactory(startDC=dc)
    },
    # {
    #     "name": "Static @0.05",
    #     "nodeType": RewardStaticNodeFactory(startDC=0.05)
    # },
    # {
    #     "name": "Static @0.1",
    #     "nodeType": RewardStaticNodeFactory(startDC=0.1)
    # },
    # {
    #     "name": "Static @0.2",
    #     "nodeType": RewardStaticNodeFactory(startDC=0.2)
    # },
    # {
    #     "name": "Static @0.25",
    #     "nodeType": RewardStaticNodeFactory(startDC=0.25)
    # },
    # {
    #     "name": "Static @0.3",
    #     "nodeType": RewardStaticNodeFactory(startDC=0.3)
    # },
    # {
    #     "name": "Static @0.5",
    #     "nodeType": RewardStaticNodeFactory(startDC=0.5)
    # },
    # {
    #     "name": "Static @0.99",
    #     "nodeType": RewardStaticNodeFactory(startDC=0.99)
    # },

], name=f"{numNodes}-nodes", numTests=500, maxTime=maxTime, numNodes=numNodes)


results = test.run()
