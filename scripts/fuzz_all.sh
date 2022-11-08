source $EMBDING_HOME/scripts/common.sh

if [ -d $EMBDING_HOME/output ]; then
    echo "Output dir already exists, not fuzzing."
    exit
fi

# Allow at most $CORES parallel jobs
open_sem $CORES

mkdir -p $EMBDING_HOME/output
for I in $PROBLEMS; do
    BINDIR=$POJ/dataset/build/bin/$I
    mkdir -p $EMBDING_HOME/output/$I
    cd $BINDIR
    for P in *; do
        run_with_lock timeout --signal=2 $TIMEOUT $AFL/afl-fuzz -i $EMBDING_HOME/seeds -o $EMBDING_HOME/output/$I/$P $BINDIR/$P
    done
done