#!/bin/bash

# Get the disk space usage for /dev/mmcblk0p2
disk_usage=$(df -h | grep '/dev/mmcblk0p2')

# Extract the used and available space
available_space=$(echo $disk_usage | awk '{print $4}')

percent_used_str=$(echo $disk_usage | awk '{print $5}')
percent_used_int=$(echo $percent_used_str | sed 's/%//')
percent_free_int=$((100 - percent_used_int))
percent_free_str="${percent_free_int}%"

# Print the formatted disk space usage
echo "$available_space disk space remaining ($percent_free_str)"

