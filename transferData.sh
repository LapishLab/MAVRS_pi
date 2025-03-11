#!/bin/bash
# requires username as 1st positional argument and path to save folder as 2nd positional argument

cd $(dirname "$(readlink -f "$0")")
path=$1@10.1.1.0:$2
echo "Started data transfer to ""$path"" at ""$(date +%H:%M:%S)"" "
rsync --recursive  --compress --progress --exclude=".*"  data/ "$path"
