#!/bin/bash
echo "git pull latest MAVRS code"
cd $(dirname "$(readlink -f "$0")")
git pull
