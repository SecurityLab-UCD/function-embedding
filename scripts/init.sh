. scripts/env.sh


if [ ! -d $LLVM ]; then
    LLVM_SRC=https://github.com/llvm/llvm-project/releases/download/llvmorg-14.0.0/$CLANG_LLVM.tar.xz
    cd $EMBDING_HOME 
    wget $LLVM_SRC 
    tar -xvf $CLANG_LLVM.tar.xz
    rm $CLANG_LLVM.tar.xz 
    mv $CLANG_LLVM clang+llvm14 
    ln -s clang+llvm14 clang+llvm 
fi

if [ ! -d $AFL ]; then
    git clone https://github.com/AFLplusplus/AFLplusplus.git
fi
cd $AFL; make -j; cd ..
