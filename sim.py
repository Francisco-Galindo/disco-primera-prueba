from multiprocessing import Pool
import sympy as sp
import time
import math

N = 5000000

def cube(x):
    print('Hola')
    return math.sqrt(x)

if __name__ == "__main__":
    with Pool() as pool:
        result = pool.map(cube, range(10, N))
    print("Program finished!")

# primes = [2]
# def addPrime(currPrimes):
#     i = currPrimes[-1]
#
#     notAdded = True
#     while notAdded:
#         i += 1
#         notAdded = False
#         for prime in currPrimes:
#             if i % prime == 0:
#                 notAdded = True
#
#     currPrimes.append(i)
#
#
#
#     return currPrimes
#
# for i in range(100):
#     primes = addPrime(primes)

primes = list(sp.primerange(1000))

def getMaxReciprocalPrime(goal) -> int:
    l = 1
    h = len(primes) - 1
    while l <= h:
        m = math.floor((l + h) / 2)
        # print(m, goal)
        if 1 / primes[m] <= goal and 1 / primes[m - 1] > goal:
            # print(1 / primes[m], goal)
            return primes[m]
        elif 1 / primes[m] > goal:
            l = m + 1
        else:
            h = m - 1
    return len(primes) - 1

primes.insert(0, 1)

duty = 0.05

p1 = getMaxReciprocalPrime(duty)
p2 = getMaxReciprocalPrime(duty - 1 / p1)

print('juan', p1, p2, 1 / p1 + 1 / p2, duty)
