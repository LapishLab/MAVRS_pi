#!/bin/bash

cd $(dirname "$(readlink -f "$0")")

echo "stopping audio"
bash mic/stopAudio.sh

echo "stopping sync record"
bash pins/stopInput.sh

echo "stopping video"
bash cam/stopVideo.sh