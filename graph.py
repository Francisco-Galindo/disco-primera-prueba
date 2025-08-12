from algos.algos import Test
from algos.fedab import FedabNodeFactory, FedabStochasticNodeFactory

# maxTime = 2000
maxTime = 400

test = Test([
    {"name": "Fedab", "nodeType": FedabNodeFactory(dutyCycle=0.05)},
    {"name": "FedabStoc", "nodeType": FedabStochasticNodeFactory(dutyCycle=0.05)},
], j=8, numTests=1, maxTime=maxTime, numNodes=3)


results = test.run()

keys = ['slot'] + list(results.keys())

line = ''
for key in keys:
    line += key + '\t'
print(line.strip())

for i in range(maxTime):
    line = ''
    for key in keys:
        if key == 'slot':
            line += f'{i}\t'
        else:
            line += f'{results[key][i]}\t'
    print(line.strip())
