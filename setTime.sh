#!/bin/bash
#First positional argument is date (YYYY-MM-DD)
#Second positional argument is time (HH:MM:SS)
echo "turning off NTP"
timedatectl set-ntp no
sleep .1
echo "setting time to $1 $2"
timedatectl set-time "$1 $2"
sleep .1
echo "turning on NTP"
timedatectl set-ntp yes

echo "time is now $(date)"

