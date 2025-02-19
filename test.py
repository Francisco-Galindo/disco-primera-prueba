from algos.algos import *

node = SearchLightNode(dutycycle=0.25)
for i in range(1,120):
    node.update(i, verbose=True)

print('\n########################################################################')

node = SearchLightRandomNode(dutycycle=0.25)
for i in range(1,120):
    node.update(i, verbose=True)
