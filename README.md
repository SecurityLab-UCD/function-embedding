# Function embedding

This repo is supposed to serve as a home to all operations whether you are using docker or running on your native server.

## Docker

`docker build .`

## Local

```sh
# Load all env vars
. script/env.sh
./script/init.sh
python3.8 -m pip install -r ./requirements.txt
python3.8 scripts/dataset.py -d C++1400 -p all 
```