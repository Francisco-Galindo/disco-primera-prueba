from algos.algos import *
import random
import simpy
import simpy.core

maxTime = 6000

test = Test([
    Algorithm(
        DiscoNode((37, 43)),
        DiscoNode((37, 43)),
        "Disco [(37, 43), (37, 43)]"),
], numTests=100, maxTime=maxTime)


# test = Test([
#     Algorithm(
#         DiscoNode((37, 43)),
#         DiscoNode((37, 43)),
#         "Disco [(37, 43), (37, 43)]"),
#     Algorithm(
#         SearchLightStripedNode(dutycycle=0.05),
#         SearchLightStripedNode(dutycycle=0.05),
#         "Searchlight-S @ 40"),
#     Algorithm(
#         SearchLightStripedRandomNode(dutycycle=0.05, alignmentOffset=1),
#         SearchLightStripedRandomNode(dutycycle=0.05, alignmentOffset=0),
#         "Searchlight-R @ 40"),
#     Algorithm(
#         SearchLightRandomNode(dutycycle=0.05, alignmentOffset=1),
#         SearchLightRandomNode(dutycycle=0.05, alignmentOffset=0),
#         "NoStripe-R @ 40"),
#     Algorithm(
#         SearchLightNode(dutycycle=0.05, alignmentOffset=1),
#         SearchLightNode(dutycycle=0.05, alignmentOffset=0),
#         "NoStripe-S @ 40"),
# ], numTests=250, maxTime=maxTime)


# test = Test([
#     Algorithm([
#         DiscoNode((17, 23)),
#         DiscoNode((191, 211)),
#     ], "Disco [(17, 23), (191, 211)]", aligned=True),
#     Algorithm([
#         SearchLightStripedNode(dutycycle=0.01, alignmentOffset=1),
#         SearchLightStripedNode(dutycycle=0.1, alignmentOffset=0),
#     ], "Searchlight-S @ 40", aligned=False),
#     Algorithm([
#         SearchLightStripedRandomNode(dutycycle=0.01, alignmentOffset=1),
#         SearchLightStripedRandomNode(dutycycle=0.1, alignmentOffset=0),
#     ], "Searchlight-R @ 40", aligned=False),
# ], numTests=1000)
#
#
# test = Test([
#     Algorithm([
#         DiscoNode((37, 43)),
#         DiscoNode((191, 211)),
#     ], "Disco [(37, 43), (191, 211)]", aligned=True),
#     Algorithm([
#         SearchLightStripedNode(dutycycle=0.01, alignmentOffset=1),
#         SearchLightStripedNode(dutycycle=0.05, alignmentOffset=0),
#     ], "Searchlight-S @ 40", aligned=False),
#     Algorithm([
#         SearchLightStripedRandomNode(dutycycle=0.01, alignmentOffset=1),
#         SearchLightStripedRandomNode(dutycycle=0.05, alignmentOffset=0),
#     ], "Searchlight-R @ 40", aligned=False),
# ], numTests=1000)


results = test.run()

# node = SearchLightStripedNode(offset=2, dutycycle=0.25)
# for i in range(1,80):
#     node.update(i)



# keys = ['slot'] + list(results.keys())
#
# line = ''
# for key in keys:
#     line += key + '\t'
# print(line.strip())
#
# for i in range(maxTime):
#     line = ''
#     for key in keys:
#         if key == 'slot':
#             line += f'{i}\t'
#         else:
#             line += f'{results[key][i]}\t'
#     print(line.strip())
