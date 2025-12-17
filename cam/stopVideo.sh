#!/bin/bash
echo "stopping any recordVideo.py processes"
pkill -15 -f recordVideo.py --echo
echo "stopVideo.sh finished"
