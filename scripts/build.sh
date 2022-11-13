#!/bin/bash
source $EMBDING_HOME/scripts/common.sh

# Allow at most $CORES parallel jobs
open_sem $CORES

# Copy the files and do some preprocessing
mkdir -p $POJ/dataset/src
mkdir -p $POJ/dataset/build/bin

for I in $PROBLEMS; do
    SRCDIR=$POJ/dataset/src/$I
    TXTDIR=$POJ/dataset/ProgramData/$I
    OUTDIR=$POJ/dataset/build/bin/$I
    mkdir -p $SRCDIR
    mkdir -p $OUTDIR
    cd $TXTDIR
    for P in *; do
        P=${P%.txt*};
        if [ ! -f $SRCDIR/$P.cpp ]; then
            # TODO: Maybe in the future use scripts, maybe even customized scripts to 
            # preprocess these programs.
            touch $SRCDIR/$P.cpp
            cat $EMBDING_HOME/header.hpp >> $SRCDIR/$P.cpp
            cat $TXTDIR/$P.txt >> $SRCDIR/$P.cpp
            sed -i 's/void main/int main/g' $SRCDIR/$P.cpp
        fi
        if [ ! -f $OUTDIR/$P ]; then
            run_with_lock $AFL/afl-clang-fast++ -O0 $SRCDIR/$P.cpp -o $OUTDIR/$P
        fi 
    done
done

# Wait for all jobs to finish
wait