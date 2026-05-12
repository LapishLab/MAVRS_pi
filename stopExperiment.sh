#!/bin/bash

cd $(dirname "$(readlink -f "$0")")

echo "stopping audio"
bash stopAudio.sh

echo "stopping sync record"
bash stopInput.sh

echo "stopping video"
bash stopVideo.sh