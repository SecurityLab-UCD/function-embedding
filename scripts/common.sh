# For colored text, refer https://stackoverflow.com/questions/5947742/how-to-change-the-output-color-of-echo-in-linux.
error() {
    echo -e "\e[1;31m[x]\e[0m" $@
    exit
}
warning() {
    echo -e "\e[1;33m[!]\e[0m" $@
}
info() {
    echo -e "\e[1;32m[-]\e[0m" $@
}

if [ -z $EMBDING_HOME ]; then
    error "EMBDING_HOME not set, please tell me where the code is."
fi
if [ -z $POJ ]; then
    error "POJ not set, please tell me where the code is."
fi
if [ -z $AFL ]; then
    error "AFL not set, please tell me where AFL++ is."
fi
if [ -z $TIMEOUT ]; then
    echo "TIMEOUT not set, please tell me how long do you want to fuzz"
fi
if [ -z $CORES ]; then
    CORES=`nproc`
    warning "CORES not set, default to all cores. (nproc = $CORES)"
fi

# Copied from StackOverflow: https://unix.stackexchange.com/questions/103920/parallelize-a-bash-for-loop
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
        if [ $? -ne 0 ]; then
            warning "$@ failed."
        fi
        # return the token semaphore
        printf 000 $? >&3
    )&
}


if [ -z $PROBLEMS ]; then
    PROBLEMS=`seq 1 104`
    info "PROBLEMS not set, default to all problems."
fi