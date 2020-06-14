#!/bin/sh

DIR="$( cd "$( dirname "%$0" )" && pwd -P )"
echo $DIR

cd $DIR
echo 'creating temp directory...'
mkdir -p 'temp'
mkdir -p 'temp/uploads'

echo 'copying source files...'
cp app.py temp
cp -r templates temp

cd temp

echo 'launching app.py...'
python app.py
