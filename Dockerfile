FROM ubuntu:22.04

RUN apt-get update && \
    apt-get -y upgrade 
ENV DEBIAN_FRONTEND noninteractive
RUN apt-get install -y -q git build-essential wget zlib1g-dev cmake python3 python3-pip ninja-build ccache && \
    apt-get clean
RUN pip install gdown

ENV HOME=/root
ENV EMBDING_HOME=$HOME
ENV AFL=$EMBDING_HOME/AFLplusplus
ENV PATH=$PATH:$HOME/clang+llvm/bin
ENV LLVM=$HOME/clang+llvm

ARG CLANG_LLVM=clang+llvm-14.0.0-x86_64-linux-gnu-ubuntu-18.04
COPY scripts/*.sh $EMBDING_HOME/scripts/
RUN cd $EMBDING_HOME && ./scripts/init.sh

COPY requirements.txt $EMBDING_HOME/requirements.txt
RUN cd $EMBDING_HOME && pip3 install -r requirements.txt

COPY scripts $EMBDING_HOME/scripts
COPY seeds $EMBDING_HOME/seeds
COPY *.[h|c]pp $EMBDING_HOME/