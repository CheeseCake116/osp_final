#!/bin/sh

DIR="$( cd "$( dirname "%$0" )" && pwd -P )"
echo $DIR

cd $DIR
echo 'creating temp directory...'
mkdir -p 'temp'


echo 'copying source files...'
cp app.py temp
cp -r template temp

cd temp

echo 'launching app.py...'
py app.py
