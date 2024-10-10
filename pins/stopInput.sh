#!/bin/bash
echo "stopping any recordInput.sh processes"
pkill -15 -f recordInput.py --echo
echo "stop recordInput.sh finished"
