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
ENV CLANG_LLVM=clang+llvm-14.0.0-x86_64-linux-gnu-ubuntu-18.04

# Install LLVM, switch to faster source if you have to.
ARG LLVM_SRC=https://github.com/llvm/llvm-project/releases/download/llvmorg-14.0.0/$CLANG_LLVM.tar.xz
RUN cd $HOME && \
    wget $LLVM_SRC && \
    tar -xvf $CLANG_LLVM.tar.xz && \
    rm $CLANG_LLVM.tar.xz && \
    mv $CLANG_LLVM clang+llvm14 && \
    ln -s clang+llvm14 clang+llvm 

# Install AFL++
RUN cd $EMBDING_HOME && \ 
    git clone https://github.com/AFLplusplus/AFLplusplus.git && \
    cd $AFL && \
    make -j

COPY scripts $EMBDING_HOME/scripts
COPY seeds $EMBDING_HOME/seeds
COPY *.[h|c]pp $EMBDING_HOME/
COPY requirements.txt $EMBDING_HOME/requirements.txt

RUN cd $EMBDING_HOME && pip3 install -r requirements.txt