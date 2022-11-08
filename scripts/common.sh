if [ -z $CORES ]; then
    CORES=`nproc`
fi
if [ -z $POJ ]; then
    echo "POJ not set, please tell me where the code is."
    exit
fi
if [ -z $AFL ]; then
    echo "AFL not set, please tell me where AFL++ is."
    exit
fi
if [ -z $TIMEOUT ]; then
    echo "TIMEOUT not set, please tell me how long do you want to fuzz"
fi

# initialize a semaphore with a given number of tokens
open_sem(){
    mkfifo pipe-$$
    exec 3<>pipe-$$
    rm pipe-$$
    local i=$1
    for((;i>0;i--)); do
        printf %s 000 >&3
    done
}

# run the given command asynchronously and pop/push tokens
run_with_lock(){
    local x
    # this read waits until there is something to read
    read -u 3 -n 3 x && ((0==x)) || exit $x
    (
     ( "$@"; )
    # push the return code of the command to the semaphore
    printf '%.3d' $? >&3
    )&
}

PROBLEMS=`seq 1 104`
# PROBLEMS=1