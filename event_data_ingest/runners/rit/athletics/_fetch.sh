#!/usr/bin/env bash

#
# Fetch stage should retrieve raw data from external source and store it unmodified
#

set -Eeuo pipefail

output_dir=""

if [ -n "${1}" ]; then
    output_dir="${1}"
else
    echo "Must pass an output_dir as first argument"
fi

### Replace the following with your implementation ###

echo "Fetching into ${output_dir}"
touch "${output_dir}/events.json"

###

# put current date as yyyy-mm-dd in $date
# -1 -> explicit current date, bash >=4.3 defaults to current time if not provided
# -2 -> start time for shell
printf -v date '%(%m/%d/%Y)T' -1

(cd "$output_dir" && curl --silent "https://ritathletics.com/services/responsive-calendar.ashx?type=month&sport=0&location=all&date=$date" -o 'events.json')
