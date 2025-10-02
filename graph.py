import os
from algos.algos import Test
from algos.fedab import FedabNodeFactory, FedabStochasticNodeFactory

# maxTime = 2500
# maxTime = 5000
maxTime = 10_000
# maxTime = 700

test = Test([
    {
        "name": "Fedab",
        "nodeType": FedabNodeFactory(dutyCycle=0.05)
    },
    {
        "name": "FedabStoc",
        "nodeType": FedabStochasticNodeFactory(dutyCycle=0.05)
    },
], numTests=1_000, maxTime=maxTime, numNodes=10)


results = test.run()
