#!/bin/bash
# Environment setup for non-docker user.
export EMBDING_HOME=`pwd`
export AFL=$EMBDING_HOME/AFLplusplus
export KELINCI=$EMBDING_HOME/kelinci
export LLVM=$HOME/clang+llvm
export PATH=$PATH:$LLVM:$AFL
export AFL_EXIT_ON_TIME=60
export AFL_NO_UI=1
unset AFL_CUSTOM_MUTATOR_LIBRARY
unset AFL_CUSTOM_MUTATOR_ONLY
export AFL_LLVM_INSTRUMENT=unset PCGUARD 
export CORES=`nproc`
unset AFL_EXIT_ON_SEED_ISSUES