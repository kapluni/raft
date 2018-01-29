import time
import logging
import sys
# import asyncio
import shelve
import socket
# from rpcudp.protocol import RPCProtocol
from fysom import Fysom
import zerorpc
from apscheduler.schedulers.gevent import GeventScheduler
# from apscheduler.schedulers.background import BackgroundScheduler
from random import randint


class LeaderState:

    # leader state
    matchIndex = {}
    nextIndex = {}

    def __init__(self, hosts, nodeState):
        for h in hosts:
            matchIndex[h] = 0
        if nodeState == None:
            for h in hosts:
                nextIndex[h] = 0
        else:
            for h in hosts:
                nextIndex[h] = nodeState.commitIndex


class NodeState:

    def __init__(self):
        self.d = shelve.open('raft.log')
        # latest term server has seen (initialized to 0 on first boot, increases monotonically)
        self.d['currentTerm'] = 0
        # candidateId that received vote in current term (or None if none)
        self.d['votedFor'] = None
        # log entries; each entry contains command for state machine, and term when entry was received by leader (first index is 1)
        self.d['log'] = []
        # index of highest log entry known to be committed (initialized to 0, increases monotonically)
        self.commitIndex = 0
        # index of highest log entry applied to state machine (initialized to 0, increases monotonically)
        self.lastApplied = 0

    def currentTerm(self):
        return self.d['currentTerm']

    def incrementCurrentTerm(self):
        self.d['currentTerm'] = self.d['currentTerm'] + 1

    def voteFor(self, candidateId):
        self.d['votedFor'] = candidateId
        self.d.sync()

    def votedFor(self):
        return self.d['votedFor']

    def entry(self, index):
        if self.index() > index:
            return self.d['log'][index]
        else:
            return None

    def checkPrevLog(self,prevLogIndex,prevLogTerm):
        return self.hasEntry(prevLogIndex) and self.entry(prevLogIndex)['term'] == prevLogTerm

    def hasEntry(self, index):
        return self.entry(index) != None

    def index(self):
        return len(self.d['log'])

    def term(self):
        if self.d['log']:
            return self.d['log'][-1]['term']
        else:
            return 0


    def appendEntries(self, term, entries):
        # If an existing entry conflicts with a new one (same index
        # but different terms), delete the existing entry and all that
        # follow it (§5.3)

        # Append any new entries not already in the log
        self.d['log']
        self.d.sync()


class Node:

    nodesInCluster=3

    # def __init__(self, nodeAddresses):
    def __init__(self):
        self.electionTimerInterval=10 #seconds timeout
        # self.electionTimerInterval=randint(2,5) #seconds timeout
        self.ns = NodeState()
        self.ownAddress = socket.gethostbyname(socket.gethostname())
        self.leaderId = None
        print(self.ownAddress)
        self.serverState = Fysom({'initial': 'follower',
                                  'events': [
                                      ('startElection', 'follower', 'candidate'),
                                      ('discoverLeader', 'candidate', 'follower'),
                                      ('newTerm', 'candidate', 'follower'),
                                      ('startElection', 'candidate', 'candidate'),
                                      ('receivedMajority', 'candidate', 'leader'),
                                      ('discoverServerWithHigherTerm',
                                       'leader', 'follower')
                                  ],
                                  'callbacks': {
                                      'onleader': self.become_leader,
                                      'onstartElection': self.become_candidate,
                                      'onleaveleader': self.stop_being_leader,
                                      'onfollower': self.become_follower
                                  }
                                  })
        self.nodeAddresses = []
        # need to make sure all nodes are started up before populating the node list
        while len(self.nodeAddresses) < self.nodesInCluster:
            self.update_node_list()
            time.sleep(1)
        print(self.nodeAddresses)

        self.otherNodeAddresses = [
            a for a in self.nodeAddresses if a != str(self.ownAddress)]
        print(self.otherNodeAddresses)

    def become_leader(self, e):
        print("============= BECOME LEADER =============")
        # • Upon election: send initial empty AppendEntries RPCs (heartbeat) to each server
        self.heartbeat = scheduler.add_job(n.append_entries_send, 'interval', seconds=5)
        if self.electionTimer:
            self.electionTimer.remove()

    def stop_being_leader(self, e):
        print("============= STOP BEING LEADER =============")
        if self.heartbeat:
            self.heartbeat.remove()

    def become_follower(self, e):
        print("============= BECOME FOLLOWER =============")
        self.electionTimer = scheduler.add_job(self.election_timer_timeout,'interval',seconds=self.electionTimerInterval)

    def initialize_clients(self):
        print("Initiailizing Clients")
        self.clients = {}
        for node in self.otherNodeAddresses:
            c = zerorpc.Client()
            c.connect("tcp://{}:1234".format(node))
            self.clients[node] = c

    def update_node_list(self):
        # dynamically look up ips in the cluster upon node creation
        self.nodeAddresses = socket.gethostbyname_ex('raft')[2]

    def append_entries(self, term, leaderId, prevLogIndex, prevLogTerm, entries, leaderCommit):
        print("APPEND ENTRIES")
        ns = self.ns
        if self.serverState.isstate('candidate'):
            self.serverState.discoverLeader()
            self.leaderId = leaderId
        if term < ns.currentTerm():
            return ns.currentTerm(), False
        elif ns.checkPrevLog(prevLogIndex,prevLogTerm):
            return ns.currentTerm(), False
        if entries != None:
            ns.appendEntries(term, entries)
        if leaderCommit > ns.commitIndex:
            ns.commitIndex = min(leaderCommit, entries.last['index'])

    def request_vote(self, term, candidateId, lastLogIndex, lastLogTerm):
        print("REQUEST VOTE")
        ns = self.ns
        if term < ns.currentTerm():
            return ns.currentTerm(), False
        # If votedFor is null or candidateId, and candidate’s log is at least as up-to-date as receiver’s log, grant vote
        if (ns.votedFor() == None or ns.votedFor() == candidateId) and lastLogIndex >= ns.commitIndex and lastLogTerm >= ns.currentTerm():
            ns.voteFor(candidateId)
            granted = True
        else:
            granted = False
        return term, granted

    def election_timer_timeout(self):
        print("ELECTION TIMER TIMEOUT")
        if self.leaderId == None and self.serverState.isstate('follower'):
            self.serverState.startElection()
    # leader methods

    # @asyncio.coroutine
    def append_entries_send(self):
        print("APPEND ENTRIES SEND")
        ns = self.ns
        entries = []
        for c in self.clients.values():
            c.append_entries(ns.currentTerm(), self.ownAddress, ns.index(), ns.currentTerm(), entries, ns.commitIndex)

        # result = yield from protocol.append_entries_receive((self.nodeAddresses[0], 1234), ns.currentTerm(), self.ownAddress, prevLogIndex, prevLogTerm, entries, leaderCommit)
        # print(result[1] if result[0] else "No response received")

    # candidate methods
    def become_candidate(self,e):
        print("============= BECOME CANDIDATE =============")
        ns = self.ns
        ns.incrementCurrentTerm()
        votes_for_current_round = self.request_vote_send()
        yesVotes = len([a for a in votes_for_current_round.values() if a['granted']==True]) + 1 # add 1 for self
        if yesVotes > self.nodesInCluster / 2:
            self.serverState.receivedMajority()
        elif self.leaderId != None and not(self.serverState.isstate('follower')):
            self.serverState.discoverLeader()
        else:
            print(self.serverState)


    def request_vote_send(self):
        print("REQUEST VOTE SEND")
        ns = self.ns
        votes_for_current_round = {}
        # would be good to do this in parallel eventually
        for id, client in self.clients.items():
            term, granted = client.request_vote(ns.currentTerm(), self.ownAddress, ns.index(), ns.term())
            votes_for_current_round[id] = {'term': term, 'granted': granted }
        return votes_for_current_round

logging.basicConfig(stream=sys.stdout, level=logging.WARN)

scheduler = GeventScheduler()

# zerorpc implementation
n = Node()
s = zerorpc.Server(n)
s.bind("tcp://0.0.0.0:1234")
n.initialize_clients()
# s = sched.scheduler(time.time, time.sleep)
scheduler.start()

s.run()

# rpcudp implementation

# loop = asyncio.get_event_loop()
# loop.set_debug(True)
#
# listen = loop.create_datagram_endpoint(Node, local_addr=('127.0.0.1', 1234))
# transport, protocol = loop.run_until_complete(listen)
#
# # Start local UDP server to be able to handle responses
# client_listen = loop.create_datagram_endpoint(RPCProtocol, local_addr=('127.0.0.1', 4567))
# client_transport, client_protocol = loop.run_until_complete(client_listen)
#
#
# try:
#     loop.run_forever()
# except KeyboardInterrupt:
#     pass
#
# transport.close()
# loop.close()
# client_transport.close()
