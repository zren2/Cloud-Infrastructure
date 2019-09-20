import math
import sys
import Queue
import threading
from termcolor import colored
import time
import random
import copy

class Process:
    Process_State = {
        'RELEASED': True,
        'WANTED': False,
        'HELD': False
    }
    Process_Voted = {
        'Voted': False
    }
    Process_Request = []
    def __init__(self):
        self.Process_State['RELEASED']= True
        self.Process_State['WANTED']=False
        self.Process_State['HELD']=False
        self.Process_Voted['Voted']=False
    def Released_State(self):
        self.Process_State['RELEASED']=True
        self.Process_State['WANTED']=False
        self.Process_State['HELD']=False
        self.Process_Voted['Voted']=False
    def Wanted_State(self):
        self.Process_State['RELEASED']=False
        self.Process_State['WANTED']=True
    def Held_State(self,Pi):
        self.Process_State['RELEASED']=False
        self.Process_State['HELD']=True
        self.Process_Request.append(Pi)
    def Reply(self,Pi):
        if self.Process_State['RELEASED'] == True and self.Process_Voted['Voted'] == False:
            self.Process_Voted['Voted']=True
            self.Held_State(Pi)
        if self.Process_State['HELD'] == True and self.Process_Voted['Voted'] == True:
            self.Process_Request.append(Pi)
    def Exit_CS_Section(self):
        self.Released_State()
    def CS_Entering_Request(self):
        self.Wanted_State()
        print('Release State: '+str(self.Process_State['RELEASED']))
    def Release_From_Pi(self):
        if len(self.Process_Request is not 0):
            self.Process_Request.pop(0)
            self.Process_Voted['Voted'] = True
        else:
            self.Process_Voted['Voted'] = False

N = 16
n = int(math.sqrt(N))
assert math.sqrt(N) ** 2 == N, "N must be a square number"
assert len(sys.argv) == 5, "Require {} arguments to function, given {}".format(
    4, len(sys.argv) - 1)
try:
    cs_int = int(sys.argv[1])
    next_req = int(sys.argv[2])
    tot_exec_time = int(sys.argv[3])
    option = int(sys.argv[4])
except ValueError:
    print("Invalid command line arguments provided. Require integers.")
    sys.exit(1)


def main():
    global threads
    threads = []
    threads.append(None)

    # Initialize threads
    for x in range(1, N + 1):
        a = []
        a.append(Queue.PriorityQueue())
        a.append({})
        a.append(threading.Thread(target=main_thread_function, args=(x,)))
        threads.append(a)

    # Start threads
    shuffled = range(1, N + 1)
    random.shuffle(shuffled)
    for x in shuffled:
        threads[x][1]['sem'] = threading.Semaphore()
        threads[x][1]['vote'] = None
        threads[x][1]['nodes'] = []
        threads[x][2].daemon = True
        threads[x][2].start()
    time.sleep(tot_exec_time)


def main_thread_function(thread_id):
    threads[thread_id][1]['state'] = "Idle"
    threads[thread_id][1]['child'] = threading.Thread(
        target=message_handler_threads, args=(thread_id,))
    threads[thread_id][1]['child'].daemon = True
    threads[thread_id][1]['child'].start()
    while 1:
        r_time = time.time()  # r_time = random.random()  #
        # print "{} - Requesting Critical".format(thread_id)
        while 1:
            threads[thread_id][1]['state'] = "Requesting"
            threads[thread_id][1]['sem'] = threading.Semaphore()
            request_critical(thread_id, r_time=r_time)
            wait_for_critical(thread_id)
            if threads[thread_id][1]['state'] is not "Failed":
                break
        print("{} - Acquired from {}").format(thread_id, " ".join([str(x) for x in threads[thread_id][1]['nodes']]))
        threads[thread_id][1]['state'] = "Acquired"
        time.sleep(cs_int / 1000.0)
        print("{} - Released").format(thread_id)
        release_critical(thread_id, r_time=r_time)
        threads[thread_id][1]['state'] = "Idle"
        time.sleep(next_req / 1000.0)


def wait_for_critical(thread_id):
    for x in range(0, 2 * n):
        threads[thread_id][1]['sem'].acquire()


def message_handler_threads(thread_id):
    while 1:
        time, msg = threads[thread_id][0].get()
        time = copy.copy(time)
        msg = copy.copy(msg)
        # if msg['action'] is not "request" and msg['action'] is not "grant":
        #    print "\t{} - Received {} from {}\n".format(thread_id, msg['action'], msg['src']),
        if msg['action'] is "request":
            if threads[thread_id][1]['vote'] is None:
                send_grant_message(thread_id, msg)
            else:
                if threads[thread_id][1]['vote'][0] > msg['tstamp']:
                    if threads[thread_id][1]['vote'][1] == msg['src']:
                        send_grant_message(thread_id, msg)
                    else:
                        send_inquire_message(thread_id, msg)
                else:
                    if threads[thread_id][1]['vote'][1] == msg['src'] and threads[thread_id][1]['vote'][0] == msg['tstamp']:
                        send_grant_message(thread_id, msg)
                    else:
                        threads[thread_id][0].put((msg['tstamp'], msg))
        elif msg['action'] is "grant":
            if msg['src'] not in threads[thread_id][1]['nodes']:
                threads[thread_id][1]['nodes'].append(msg['src'])
                print("\t{}({:.6f}) - Received {} from {}. Votes: {}\n").format(thread_id, msg['tstamp'], msg['action'], msg['src'], " ".join([str(x) for x in threads[thread_id][1]['nodes']])),
                threads[thread_id][1]['sem'].release()
        elif msg['action'] is "release":
            threads[thread_id][1]['vote'] = None
        elif msg['action'] is "failed":
            msg['action'] = 'request'
            msg['src'] = msg['alternative']
            msg.pop('alternative')
            threads[thread_id][0].put((msg['tstamp'], msg))
        elif msg['action'] is "inquire":
            state = threads[thread_id][1]['state']
            if (state is "Requesting" or state is "Idle"):
                threads[thread_id][1]['state'] = "Failed"
                for x in range(2 * n):
                    threads[thread_id][1]['sem'].release()
                send_relinquish_message(thread_id, msg)
            else:
                send_failed_message(thread_id, msg)
        elif msg['action'] is "relinquish":
            if threads[thread_id][1]['vote'] is not None and threads[thread_id][1]['vote'][1] is msg['src']:
                msg['src'] = msg['alternative']
                msg['action'] = "grant"
                msg.pop('alternative')
                send_grant_message(thread_id, msg)
            else:
                print("\t{} - Old RELINQUISH received from {}. Alternative: {}.\n").format(thread_id, msg['src'], msg['alternative']),
        else:
            print(colored("Unknown action '{}' received!", "red")).format(msg['action'])


def send_message(dst, msg):
    threads[dst][0].put((msg['tstamp'], msg))


# Reply to src.
def send_grant_message(thread_id, imsg):
    # print "\t{} sending GRANT to {}\n".format(thread_id, imsg['src']),
    threads[thread_id][1]['vote'] = (imsg['tstamp'], imsg['src'])
    imsg['action'] = 'grant'
    dst = imsg['src']
    imsg['src'] = thread_id
    send_message(dst, imsg)


# Reply to src with original message.
def send_failed_message(thread_id, imsg):
    # print "\t{} sending FAILED to {}. State: {}\n".format(thread_id, imsg['src'], threads[thread_id][1]['state']),
    dst = imsg['src']
    imsg['src'] = thread_id
    imsg['action'] = 'failed'
    send_message(dst, imsg)


# Reply to current voted node with same message, set alternative.
def send_inquire_message(thread_id, imsg):
    # print "\t{} sending INQUIRE to {}. Alternative: {}\n".format(thread_id, threads[thread_id][1]['vote'][1], imsg['src']),
    imsg['alternative'] = imsg['src']
    imsg['src'] = thread_id
    imsg['action'] = 'inquire'
    send_message(threads[thread_id][1]['vote'][1], imsg)


# Reply to src with same message.
def send_relinquish_message(thread_id, imsg):
    dst = imsg['src']
    imsg['src'] = thread_id
    imsg['action'] = 'relinquish'
    send_message(dst, imsg)


def request_critical(thread_id, r_time=time.time()):
    threads[thread_id][1]['nodes'] = []
    msg = {
        "action": "request",
        "src": thread_id,
        "tstamp": r_time
    }
    send_to_voting_set(thread_id, msg)


def release_critical(thread_id, r_time=time.time()):
    msg = {
        "action": "release",
        "src": thread_id,
        "tstamp": r_time
    }
    send_to_voting_set(thread_id, msg)


def send_to_voting_set(thread_id, msg):
    try:
        gen = voting_set(thread_id)
        while 1:
            send_message(gen.next(), msg)
    except StopIteration:
        pass


def voting_set(Node,Cluster):
    voting_set = dict()
    K = int(math.ceil(math.sqrt(Node)))
    (row_id, col_id) = (int(Node / K),
                        int(Node % K))
    for i in range(K):
        voting_set[K * row_id + i] = None
        voting_set[col_id + K * i] = None
    return voting_set

Nodes= input("Insert Number Of Nodes (N): ")
Clusters= input("Insert Number of K:")
#print int(math.sqrt(Nodes))
if(int(math.sqrt(Nodes)) != int(Clusters) or Clusters > Nodes):
    print("Cluster should be less than Square Root of Nodes!")
else:
    qourum=[]
    prosesses = []
    for i in xrange(Nodes):
        prosesses.insert(i,Process())
    # print(prosesses[1].Process_State)
    # prosesses[0].CS_Entering_Request()
    # print(prosesses[0].Process_State)
    shuffle= xrange(1,int(Clusters)*(int(Clusters)-1)+1)
    print voting_set(Nodes,Clusters)
    for j in xrange(Nodes):
        qourum.insert(j,voting_set(Nodes,Clusters))
        #print(qourum[j])
