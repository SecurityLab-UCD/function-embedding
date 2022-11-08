source $EMBDING_HOME/scripts/common.sh

if [ -z $1 ]; then
    echo "I wasn't given a file to fuzz."
    exit
fi

if [ -z $OUTPUT ]; then
    echo "OUTPUT unset, I wasn't given an output"
    exit
fi

timeout --signal=2 $TIMEOUT $AFL/afl-fuzz -i $EMBDING_HOME/seeds -o $OUTPUT $1