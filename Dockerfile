FROM python:3.6.4-jessie

RUN pip install zerorpc fysom apscheduler
# RUN apt-get -qq update \
#      && apt-get -qq install -y software-properties-common \
#     && add-apt-repository "deb http://security.debian.org/ jessie/updates main contrib non-free" \
#     && apt-get update \
#     && apt-get install -y  dnsutils

COPY py /py

ENTRYPOINT ["python", "py/raft.py"]
