#!/bin/bash

cd $(dirname "$(readlink -f "$0")")
rm -rf data/*