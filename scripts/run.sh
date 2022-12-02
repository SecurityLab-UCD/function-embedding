#!/bin/bash
source $EMBDING_HOME/scripts/common.sh

if [ -z $OUTPUT ]; then
    warning "OUTPUT is not set, using default: $EMBDING_HOME/output"
    export OUTPUT=$EMBDING_HOME/output
fi
if [ ! -d $OUTPUT ]; then
    warning "OUTPUT doesn't exist."
    exit
fi

# Allow at most $CORES parallel jobs
open_sem $CORES

for I in $PROBLEMS; do
    BINDIR=$POJ/dataset/build/bin/$I
    cd $OUTPUT/$I
    mkdir -p $ERROUT/$I
    info "Running $I"
    for P in *; do
        FUZZOUT=$OUTPUT/$I/$P/default
        # if [ ! -d $FUZZOUT/output ] && [ -d $FUZZOUT/queue ]; then
        if [ -d $FUZZOUT/queue ]; then
            mkdir -p $FUZZOUT/output
            mkdir -p $FUZZOUT/input_csv
            cd $FUZZOUT/queue
            for Q in *; do
                info $FUZZOUT/queue/$Q
                # Has to use bash or the stdin/stdout redirector will be ignored.
                run_with_lock timeout 1\
                    bash -c\
                    "$POJ/dataset/build/bin/$I/$P < $FUZZOUT/queue/$Q 1> $FUZZOUT/output/$Q 2> $FUZZOUT/input_csv/$Q.csv"
            done
        fi
    done
done
