# Copied from StackOverflow: https://unix.stackexchange.com/questions/103920/parallelize-a-bash-for-loop
if [ -z $CORES ]; then
    CORES=`nproc`
fi
if [ -z $POJ ]; then
    echo "POJ not set, please tell me where the code is."
    exit
fi
if [ -z $AFL ]; then
    echo "Please tell me where AFL++ is."
    exit
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

open_sem $CORES

PROBLEMS=`seq 1 104`
# PROBLEMS=1

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
