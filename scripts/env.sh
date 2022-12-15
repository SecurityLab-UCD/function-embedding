#!/bin/bash
# Environment setup for non-docker user.
export EMBDING_HOME=`pwd`
export POJ=$EMBDING_HOME/CodeXGLUE/Code-Code/Clone-detection-POJ-104/
export TIMEOUT=60
export AFL=$EMBDING_HOME/AFLplusplus
export LLVM=$HOME/clang+llvm
export AFL_EXIT_ON_TIME=60
export AFL_NO_UI=1
unset AFL_CUSTOM_MUTATOR_LIBRARY
unset AFL_CUSTOM_MUTATOR_ONLY
export AFL_LLVM_INSTRUMENT=unset PCGUARD 