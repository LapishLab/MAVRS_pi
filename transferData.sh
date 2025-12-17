#!/bin/bash
# requires username as 1st positional argument and path to save folder as 2nd positional argument

cd $(dirname "$(readlink -f "$0")")
path=$1@10.1.1.0:$2
echo "Started data transfer to ""$path"" at ""$(date +%H:%M:%S)"" "
rsync -ah --info=progress2 --exclude=".*"  data/ "$path"

if [ $? -eq 0 ]; then
    echo
    echo "---Transfer Complete---"
    echo "It is safe to delete data from this Pi"
    echo "-----------------------"
    echo
else
    echo
    echo "---WARNING---"
    echo "Data transfer failed! "
    echo "-------------"
    echo
fi

