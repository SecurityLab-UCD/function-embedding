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
    for P in *; do
        FUZZOUT=$OUTPUT/$I/$P/default
        if [ ! -d $FUZZOUT/output ]; then
            mkdir -p $FUZZOUT/output
            cd $FUZZOUT/queue
            for Q in *; do
                # Has to use bash or the stdin/stdout redirector will be ignored.
                run_with_lock bash -c "$POJ/dataset/build/bin/$I/$P < $Q > $FUZZOUT/output/$Q" 
            done
        fi
    done
done