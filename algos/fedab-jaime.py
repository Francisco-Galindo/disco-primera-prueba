import random

import simpy
from simpy.util import start_delayed
import matplotlib.pyplot as plt
import math

PLOT = False

def Slots(number):
    return 1000000000*number

class Stats:
    def __init__(self):
        self.collisions = []
        self.collisions_extra = []
        self.neighbors_found = []
        self.found_all_time = []

    def __add__(self, other):
        self.collisions += other.collisions
        self.collisions_extra += other.collisions_extra
        self.neighbors_found += other.neighbors_found
        self.found_all_time += other.found_all_time
        return self

    def __str__(self):
        ret = 'Collisions in normal: ' + str(self.collisions) + '\n'
        ret += 'Collisions in scheduled: ' + str(self.collisions_extra) + '\n'
        ret += 'Neighbors found: ' + str(self.neighbors_found) + '\n'
        ret += 'Found-all time: ' + str(self.found_all_time) + '\n'
        return ret

    def save_to_file(self, filename):
        f = open(filename+'.csv', 'w')
        length = len(self.collisions)
        for i in range(length):
            f.write(str(self.collisions[i])+';'+str(self.collisions_extra[i])+';'+str(self.neighbors_found[i])+';'+str(self.found_all_time[i])+'\n')
        f.close()

class Node:
    def __init__(self, id, env, nvecinos, r):
        self.id = id
        self.state = 0 #0: Sleeping, 1: Transmitting: 2: Receiving
        self.vecinos = {}
        self.env = env
        self.recepciones = {}
        self.transmisiones = []
        self.nvecinos = nvecinos
        self.collisions = 0
        self.collisions_extra = 0
        self.r = r

    def save_vecinos_to_file(self, filename):
        f = open(filename+'.csv', 'a')
        encuentros =[]
        for k in self.vecinos:
            encuentros.append(min(self.vecinos[k]))
        discoveries = sorted(encuentros)
        for t in discoveries:
            f.write(str(t/Slots(1))+';')
        f.write('\n')
        f.close()

    def set_maxshift(self, shift):
        self.maxshift = shift

    def set_my_shift(self, shift):
        self.my_shift = int(Slots(1) * (shift / Slots(1) - shift // Slots(1)))

    def get_state(self):
        return self.state

    def add_vecino(self, vecino, time):
        if time >= self.maxshift:
            if vecino not in self.vecinos:
                self.vecinos[vecino] = []
                #print('Nuevo encuentro: ', self.id, '->', vecino, '(', time / Slots(1), ')')
            self.vecinos[vecino].append(time-self.maxshift)
            if self.id == 0:
                if len(self.vecinos) >= self.nvecinos-1:
                    #self.env.process(finish(self.env))
                    pass

    def count_vecinos(self):
        return len(self.vecinos)

    def add_recepcion(self, id):
        if len(self.recepciones) == 0:
            self.recepciones[id] = True
        else:
            for k in self.recepciones:
                self.recepciones[k] = False
            self.recepciones[id] = False

    def pop_recepcion(self, id):
        if id in self.recepciones:
            return self.recepciones.pop(id) and self.state == 2
        else:
            return False

    def add_transmision(self, id):
        self.transmisiones.append(id)

    def found_all_neighbors(self):
        return self.count_vecinos() >= self.nvecinos - 1

    def check_finish(self):
        while True:
            yield self.env.timeout(Slots(1))
            if self.found_all_neighbors():
                break

    def get_last_neighbor_time(self):
        maxim = 0
        for k in self.vecinos:
            minimum = min(self.vecinos[k])
            if minimum > maxim:
                maxim = minimum
        return maxim

class Fedab_node(Node):
    def start(self, time, p):
        self.tx_count = 0
        yield self.env.timeout(time)
        self.env.process(self.start_cycle(p))
        #self.env.process(self.start_rx())
        #yield self.env.timeout(Slots(1)-self.txtime)
        #self.env.process(self.start_tx())

    def start_cycle(self, p):

        start_delayed(self.env, self.start_cycle(p), Slots(self.m * self.n))

        delay = 0
        u = self.r.uniform(0,1)
        if u < p:
            delay = self.r.randint(0, Slots(self.m))

        yield self.env.timeout(delay)
        self.env.process(self.start_rx())
        for i in range(1,self.n):
            start_delayed(self.env, self.start_rx(), i*Slots(self.m))
        for i in range(math.ceil(self.m/2)):
            start_delayed(self.env, self.start_tx(), (i+2)*Slots(1)-self.txtime)



    def set_m(self, m):
        self.m = m
        self.tx_total = math.ceil(m/2)

    def set_n(self, n):
        self.n = n

    def set_txduration(self, txd):
        self.txtime = txd

    def set_nodes(self, nodes):
        self.nodes = nodes

    def start_rx(self):
        #The following start
        self.next_on = self.env.now + Slots(self.m)
        #Change the state
        self.state = 2
        #print('RxStart ',self.env.now/Slots(1))
        yield self.env.timeout(Slots(1))
        self.env.process(self.end_rx())


    def end_rx(self):
        # print('RxEnd ', self.env.now/Slots(1))
        wait = 0
        if len(self.recepciones) > 0:
            wait = self.txtime + 1
            yield self.env.timeout(wait)
        self.state = 0
        if PLOT:
            plt.plot([(self.env.now - Slots(1) - wait) / Slots(1), self.env.now / Slots(1)], [self.id, self.id])
        yield self.env.timeout(0)

    def start_tx(self):
        self.state = 1
        #print(self.id,'TxStart ', self.env.now/Slots(1),' Count: ',self.tx_count)
        for k in self.nodes:
            if self.nodes[k].get_state() == 2:
                self.nodes[k].add_recepcion(self.id)
                self.add_transmision(k)
        yield self.env.timeout(self.txtime)
        self.env.process(self.end_tx())

    def end_tx(self):
        self.state = 0
        if PLOT:
            plt.plot([(self.env.now-self.txtime)/Slots(1), (self.env.now)/Slots(1)], [self.id, self.id])
        #Check if someone received correctly
        for n in self.transmisiones:
            state = self.nodes[n].pop_recepcion(self.id)
            if state:
                diff = (self.my_shift - self.nodes[n].my_shift + Slots(1)) % Slots(1)
                if PLOT:
                    if n == 0:
                        plt.axvline(x=self.env.now / Slots(1))
                    elif self.id == 0:
                        plt.axvline(x=self.env.now / Slots(1), color='red')
                self.nodes[n].add_vecino(self.id, self.env.now)
                self.env.process(self.nodes[n].start_extra_tx(self.next_on-self.env.now+diff))
            else:
                self.nodes[n].collisions += 1
        self.transmisiones.clear()
        yield self.env.timeout(0)

    def start_extra_tx(self,delay):
        yield self.env.timeout(delay)
        #print('ExtraTxStart ', self.env.now / Slots(1))
        self.state = 1
        for k in self.nodes:
            if self.nodes[k].get_state() == 2:
                self.nodes[k].add_recepcion(self.id)
                self.add_transmision(k)
        yield self.env.timeout(self.txtime)
        self.env.process(self.end_extra_tx())

    def end_extra_tx(self):
        #print('ExtraTxEnd ', self.env.now / Slots(1))
        if PLOT:
            plt.plot([(self.env.now-self.txtime)/Slots(1), (self.env.now)/Slots(1)], [self.id, self.id])
        # Check if someone received correctly
        for n in self.transmisiones:
            state = self.nodes[n].pop_recepcion(self.id)
            if state:
                if PLOT:
                    if n == 0:
                        plt.axvline(x=self.env.now/Slots(1))
                    elif self.id == 0:
                        plt.axvline(x=self.env.now / Slots(1), color='red')
                self.nodes[n].add_vecino(self.id, self.env.now)
            else:
                self.nodes[n].collisions_extra += 1
        yield self.env.timeout(0)
        self.transmisiones.clear()

class Fedab:
    def __init__(self, nodes, duty, alpha, seed):
        #print('DUTY: ',duty)
        self.m = math.ceil(2 / duty)
        self.n = math.ceil(alpha/duty)
        while (self.n+math.ceil((self.m-1)/2)*alpha)/(self.n * self.m) < duty:
            self.m -= 1
        #This two are to minimize the worst-case discovery delay
        self.T = self.n * self.m
        self.duty = (self.n+math.ceil((self.m-1)/2)*alpha)/self.T
        self.txduration = Slots(1)*alpha
        self.nodes = {}
        self.nnodes = nodes
        self.seed = seed
        self.env = simpy.Environment()

    def print(self):
        print('duty: ', self.duty)
        print('n: ',self.n)
        print('m: ', self.m)
        print('T: ', self.T)
        print('txduration: ', self.txduration)
        print('#nodes: ', self.nnodes)
        print('Seed: ', self.seed)

    def run(self,maxtime, p):
        import random as r
        r.seed(self.seed)
        self.maxshift = 0
        for i in range(self.nnodes):
            self.nodes[i] = Fedab_node(i, self.env, self.nnodes, r)
            self.nodes[i].set_n(self.n)
            self.nodes[i].set_m(self.m)
            self.nodes[i].set_txduration(self.txduration)
            self.nodes[i].set_nodes(self.nodes)
            shift = r.randint(0, Slots(self.T))
            self.nodes[i].set_my_shift(shift)
            if self.maxshift < shift:
                self.maxshift = shift
            self.env.process(self.nodes[i].start(shift, p))
        for i in range(self.nnodes):
            self.nodes[i].set_maxshift(self.maxshift)


        finishp = self.env.process(self.nodes[0].check_finish()) #Checks by polling if it's over
        from simpy.events import AnyOf
        a = AnyOf(self.env, [self.env.timeout(maxtime+self.maxshift), finishp])
        self.env.run(a)

        #print('Stopped on', self.env.now/Slots(1))

        if PLOT:
            plt.show()

        #Stats recover
        s = Stats()
        s.collisions.append(self.nodes[0].collisions)
        s.collisions_extra.append(self.nodes[0].collisions_extra)
        s.neighbors_found.append(len(self.nodes[0].vecinos))
        if self.nodes[0].found_all_neighbors():
            s.found_all_time.append( (self.nodes[0].get_last_neighbor_time())/Slots(1) )
        else:
            s.found_all_time.append( maxtime/Slots(1) )

        return s, self.nodes[0]

def run_simulations(nodes, duty, alpha, seeds, start_seed, p, maxslots=100000):
    filename = 'Fedab_'+str(nodes)+'nodes_'+str(int(duty*100))+'d_'+str(seeds)+'seeds_'+str(start_seed)+'startseed_'+str(int(p*100))+'p'
    filename2 = 'Fedab_' + str(nodes) + 'nodes_' + str(int(duty * 100)) + 'd_' + str(seeds) + 'seeds_' + str(start_seed) + 'startseed_' + str(int(p * 100)) + 'p_DISCOVERIES'
    s = Stats()
    for seed in range(start_seed+1,start_seed+seeds+1):
        if seed % (seeds/100) == 0:
            f = open('PrintsFedab_'+str(nodes)+'n_'+str(p)+'p_'+str(duty)+'d.txt','a')
            f.write(str(seed/(seeds/100))+'%\n')
            f.close()
        f = Fedab(nodes, duty, alpha, seed)
        r, n = f.run( Slots(1)*maxslots, p )
        s += r
        n.save_vecinos_to_file(filename2)
    s.save_to_file(filename)
    return s

def run_simulations_multip(nproc, nodes, duty, alpha, seeds, start_seed, p, maxslots=100000):
    from multiprocessing import Process

    seeds_per_proc = math.ceil(seeds / nproc)
    print('Multiprocessing run')
    print('Processors:',nproc)
    print('Seeds per processor:', seeds_per_proc)

    procs = []
    for i in range(nproc):
        print('Proceso iniciado! '+str(seeds_per_proc)+' semillas desde la '+str(start_seed+i*seeds_per_proc))
        pr = Process(target=run_simulations, args=(nodes, duty, alpha, seeds_per_proc, start_seed+i*seeds_per_proc, p, maxslots))
        procs.append(pr)
        pr.start()
    for proc in procs:
        proc.join()

    join_files(nproc, nodes, duty, seeds, start_seed, p)


def join_files(nproc, nodes, duty, seeds, start_seed, p):
    seeds_per_proc = math.ceil(seeds / nproc)
    filename = 'Fedab_' + str(nodes) + 'nodes_' + str(int(duty * 100)) + 'd_' + str(seeds) + 'seeds_' + str(
        start_seed) + 'startseed_' + str(int(p * 100)) + 'p.csv'
    ffinal = open(filename, 'w')
    for i in range(nproc):
        filename = 'Fedab_' + str(nodes) + 'nodes_' + str(int(duty * 100)) + 'd_' + str(
            seeds_per_proc) + 'seeds_' + str(start_seed + i * seeds_per_proc) + 'startseed_' + str(
            int(p * 100)) + 'p.csv'
        f = open(filename, 'r')
        lines = f.readlines()
        for l in lines:
            ffinal.write(l)
        f.close()
    ffinal.close()

    filename = 'Fedab_' + str(nodes) + 'nodes_' + str(int(duty * 100)) + 'd_' + str(seeds) + 'seeds_' + str(
        start_seed) + 'startseed_' + str(int(p * 100)) + 'p_DISCOVERIES.csv'
    ffinal = open(filename, 'w')
    for i in range(nproc):
        filename = ('Fedab_' + str(nodes) + 'nodes_' + str(int(duty * 100)) + 'd_' + str(seeds_per_proc) + 'seeds_' +
                    str(start_seed + i * seeds_per_proc) + 'startseed_' + str(int(p * 100)) + 'p_DISCOVERIES.csv')
        f = open(filename, 'r')
        Lines = f.readlines()
        for l in Lines:
            ffinal.write(l)
        f.close()
    ffinal.close()

class StatsFile:
    def __init__(self, filename):
        filename2 = filename.split('.cs')[0]+'_DISCOVERIES.csv'
        f = open(filename,'r')
        f2 = open(filename2, 'r')
        lines = f.readlines()
        self.collisions = []
        self.collisions_extra = []
        self.neighbors_found = []
        self.found_all_time = []
        for l in lines:
            data = l.split(';')
            self.collisions.append(float(data[0]))
            self.collisions_extra.append(float(data[1]))
            self.neighbors_found.append(float(data[2]))
            self.found_all_time.append(float(data[3]))

        lines = f2.readlines()
        self.s = []
        for l in lines:
            data = l.split(';')
            dl = []
            for d in data:
                if d != '':
                    try:
                        dl.append(float(d))
                    except:
                        pass
                else:
                    dl.append(0)
            self.s.append(dl)

    def get_cdf(self):
        cdf = []
        for i in range(math.ceil(max(self.found_all_time))+1):
            cdf.append(0)
        for f in self.found_all_time:
            cdf[math.ceil(f)] += 1
        length = len(self.found_all_time)
        for i in range(1,len(cdf)):
            cdf[i] = cdf[i-1] + cdf[i]/length
        return cdf

    def get_collisions_cdf(self):
        cdf = []
        for i in range(math.ceil(max(self.collisions)+max(self.collisions_extra))+1):
            cdf.append(0)
        length = len(self.collisions)
        for i in range(length):
            cdf[math.ceil(self.collisions[i]+self.collisions_extra[i])] += 1
        for i in range(1,len(cdf)):
            cdf[i] = cdf[i-1] + cdf[i]/length
        return cdf

    def get_encuentros_cdf(self):
        cdf = []
        for i in range(math.ceil(max(self.neighbors_found))+1):
            cdf.append(0)
        length = len(self.neighbors_found)
        for i in range(length):
            cdf[math.ceil(self.neighbors_found[i])] += 1
        for i in range(1,len(cdf)):
            cdf[i] = cdf[i-1] + cdf[i]/length
        return cdf

    def get_interencuentros_cdf(self):
        cdf = []
        tiempos = []
        for s in self.s:
            last = 0
            for d in s:
                tiempos.append(d-last)
                last = d
        for s in range(math.ceil(max(tiempos))+1):
            cdf.append(0)
        length = len(tiempos)
        for i in range(length):
            cdf[math.ceil(tiempos[i])] += 1
        for i in range(1,len(cdf)):
            cdf[i] = cdf[i-1] + cdf[i]/length
        return cdf

    def simplify_plot(line, points):
        l = math.floor(len(line)/points)
        x = []
        y = []
        for i in range(points):
            x.append(i*l)
            y.append(line[i*l])
        return x,y

def plot_stats(fig, ax, n, d, p):
    s = StatsFile('res/Fedab_' + str(n) + 'nodes_' + str(d) + 'd_10000seeds_0startseed_' + str(p) + 'p.csv')
    x, y = StatsFile.simplify_plot(s.get_collisions_cdf(), 200)
    l1, = ax[0,0].plot(x, y, label='Fedab '+str(n)+'n '+str(d)+'d '+str(p)+'p')
    ax[0,0].set_title("Collisions")

    x, y = StatsFile.simplify_plot(s.get_cdf(), 200)
    l2, = ax[0,1].plot(x, y, label='Fedab '+str(n)+'n '+str(d)+'d '+str(p)+'p')
    ax[0,1].set_title("CDF 100% discoveries")
    print(x)
    print(y)

    y = s.get_encuentros_cdf()
    l3, = ax[1,0].plot(y, label='Fedab '+str(n)+'n '+str(d)+'d '+str(p)+'p')
    ax[1,0].set_title("CDF # of discoveries")

    y = s.get_interencuentros_cdf()
    l4, = ax[1,1].plot(y, label='Fedab '+str(n)+'n '+str(d)+'d '+str(p)+'p')
    ax[1,1].set_title("CDF inter-discoveries time")

    return l1, l2, l3, l4

if __name__ == '__main__':
    import sys

    n = 20
    d = 0.01
    seeds = 10000
    p = 1.0
    f=0
    proc = 100

    nargs = len(sys.argv)
    for i in range(1, nargs):
        ar = sys.argv[i].split('=')
        if ar[0] == 'nodes':
            n = int(ar[1])
        elif ar[0] == 'd':
            d = float(ar[1])/100
        elif ar[0] == 's':
            seeds = int(ar[1])
        elif ar[0] == 'p':
            p = float(ar[1])
        elif ar[0] == 'f':
            f = int(ar[1])
        elif ar[0] == 'proc':
            proc = int(ar[1])
        else:
            print ('Parametro '+ar[0]+' invalido')
            sys.exit([0])

    print('Starting simulation for \nn='+str(n)+'\nd='+str(d)+'\nseeds='+str(seeds)+'\np='+str(p)+'\n')

    #sims = run_simulations_multip(proc,n, d, 0.0056, seeds, f, p)
    #sims = run_simulations(100, 0.01, 0.0056, 1, 0, 0.1)

    #join_files(proc, n, d, seeds, f, p)

    fig, ax = plt.subplots(2, 2)
    snodes=20
    sduty = 1
    sps = [0, 100]
    l = []
    for i in range(4):
        l.append([])
    for sp in sps:
        lines = plot_stats(fig, ax, n= snodes, d=sduty, p=sp)
        for i in range(4):
            l[i].append(lines[i])
    ax[0,0].legend(handles=l[0])
    ax[0,1].legend(handles=l[1])
    ax[1,0].legend(handles=l[2])
    ax[1,1].legend(handles=l[3])

    plt.show()
