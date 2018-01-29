# Gamalon Interview Problem

## Summary

The implementation does not fully implement RAFT. I focused on setting up a reasonable test configuration, and completed leader election, and started on the entry tracking, but did not fully complete it. A few more hours probably would do it.

## Running

You need to install docker (0.17) to be able to run the example. Docker will take care of setting up all the dependencies. By using a docker network with internal dns resolution, we are able to get the full list of ips on service startup using DNS. this would also be helpful if you ever wanted to implement dynamic cluster membership changes.

To run, execute the following:

```sh
# create network for node deployment
docker network create --driver overlay raftnet
# build node image
docker build -t raft:latest .
# create and start raft cluster with 5 nodes using the created network and image
docker service create --endpoint-mode dnsrr --replicas 5 --name raft --network raftnet raft:latest
# tail the logs on all the nodes to monitor the state
docker service logs -f raft
```

In the logs, you can see the state machine transitions for the node state, so you can see when a node becomes a candidate, the votes they get, and who ultimately gets elected leader.

### Appending data

To send data to the leader, you have to grab the leader ip address, and execute the send on one of the containers.

```sh
# get a container id
docker ps
CONTAINER ID        IMAGE               COMMAND               CREATED             STATUS              PORTS               NAMES
63a55218849a        raft:latest         "python py/raft.py"   2 hours ago         Up 2 hours                              raft.4.hxffahw353kr4qcfxjvv73s26
b801834136b1        raft:latest         "python py/raft.py"   2 hours ago         Up 2 hours                              raft.2.ub4eusi1b3m7y9l2d3er9jc08

# send an rpc call from within a container, assuming the leader is at 10.0.0.81
docker exec -it 63a55218849a zerorpc --connect tcp://10.0.0.81:1234 leader_add_entry '{"test": "test"}'
```

## Design notes

* State is encapsulated in the `NodeState` class, with persistent state stored using the python shelf library.
* Scheduling is done using the `APscheduler` library, using gevent for multiple execution path triggering
* RPC is done using zerorpc, which uses gevent and zeromq. I selected this largely due to the simplicity of the API, and swapping in a different implementation would be straightforward.
* The code is pretty rough in general - it would benefit from a refactoring pass, and my intent was to talk through the module composition in-person.

# THANKS

Thanks to everyone who met with me today. You guys have an impressive company and a great team, and I appreciate meeting all of you very much :) .
