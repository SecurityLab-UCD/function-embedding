#!/bin/bash
source $EMBDING_HOME/scripts/common.sh

if [ -z $OUTPUT ]; then
    warning "OUTPUT is not set, using default: $EMBDING_HOME/output"
    export OUTPUT=$EMBDING_HOME/output
fi
if [ -d $OUTPUT ]; then
    warning "Output dir already exists."
fi

# Allow at most $CORES parallel jobs
open_sem $CORES

mkdir -fp $OUTPUT
for I in $PROBLEMS; do
    BINDIR=$POJ/dataset/build/bin/$I
    mkdir -p $OUTPUT/$I
    cd $BINDIR
    for P in *; do
        FUZZOUT=$OUTPUT/$I/$P
        if [ ! -d $FUZZOUT ]; then
            run_with_lock $AFL/afl-fuzz -V $TIMEOUT -i $EMBDING_HOME/seeds -o $FUZZOUT $BINDIR/$P
            # Give afl-fuzz sometime to bind core.
            sleep 0.5
        fi
    done
done

# Wait for all jobs to finish
wait