. scripts/env.sh

# Which LLVM are we using?
if [ ! -d $CLANG_LLVM]; then
    CLANG_LLVM=clang+llvm-14.0.0-x86_64-linux-gnu-ubuntu-18.04
fi

# Download and install LLVM
if [ ! -d $LLVM ]; then
    LLVM_SRC=https://github.com/llvm/llvm-project/releases/download/llvmorg-14.0.0/$CLANG_LLVM.tar.xz
    cd $EMBDING_HOME 
    wget $LLVM_SRC 
    tar -xvf $CLANG_LLVM.tar.xz
    rm $CLANG_LLVM.tar.xz 
    mv $CLANG_LLVM clang+llvm14 
    ln -s clang+llvm14 clang+llvm 
fi

# Download and install AFL
if [ ! -d $AFL ]; then
    git clone https://github.com/AFLplusplus/AFLplusplus.git
fi
cd $AFL; make -j; cd ..

if [ ! -d $KELINCI ]; then
    git clone https://github.com/isstac/kelinci.git
fi
cd $KELINCI/fuzzerside; make -j
cd $KELINCI/instrumentor; gradle build
cd $EMBDING_HOME
