docker service rm raft && \
  docker build -t raft:latest . && \
  sleep 10 && \
  docker service create --endpoint-mode dnsrr --replicas 3 --name raft --network raftnet raft:latest && \
  docker service logs -f raft
