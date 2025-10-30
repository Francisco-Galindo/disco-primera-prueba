from algos.algos import Test
from algos.fedab import FedabNodeFactory, FedabStochasticNodeFactory
from algos.reward import RewardNodeFactory, Reward2NodeFactory, Reward3NodeFactory, Reward4NodeFactory

# maxTime = 2500
# maxTime = 5000
# maxTime = 10_000
# maxTime = 700
maxTime = 1500

test = Test([
    # {
    #     "name": "Fedab",
    #     "nodeType": FedabNodeFactory(dutyCycle=0.05)
    # },
    {
        "name": "FedabStoc",
        "nodeType": FedabStochasticNodeFactory(dutyCycle=0.05)
    },
    {
        "name": "Reward",
        "nodeType": RewardNodeFactory(startDC=0.03)
    },
    {
        "name": "Reward2",
        "nodeType": Reward2NodeFactory(startDC=0.02)
    },
    {
        "name": "Reward3",
        "nodeType": Reward3NodeFactory(startDC=0.02)
    },
    {
        "name": "Reward4",
        "nodeType": Reward4NodeFactory(startDC=0.02)
    },
], numTests=1_000, maxTime=maxTime, numNodes=10)


results = test.run()
