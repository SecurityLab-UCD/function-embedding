CC = ${LLVM}/bin/clang++

all: example

encode2stderr.so:	encode2stderr.cpp encode2stderr.hpp
	$(CC) -fPIC -shared encode2stderr.cpp -o encode2stderr.so

example: encode_example.cpp encode2stderr.so
	$(CC) encode_example.cpp ./encode2stderr.so -o example -D_ENCODE_INPUT_

clean:
	rm *.so example