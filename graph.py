from algos.algos import *
import random
import simpy
import simpy.core

from algos.fedab import FedabNodeFactory

maxTime = 2000

test = Test([
    {"name": "Fedab", "nodeType": FedabNodeFactory(dutyCycle=0.05)},
], numTests=100, maxTime=maxTime, numNodes=2)


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
