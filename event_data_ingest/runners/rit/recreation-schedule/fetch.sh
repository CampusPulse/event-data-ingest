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

(cd "$output_dir" && curl --silent "https://recreation.rit.edu/Facility/GetScheduleCustomAppointments?selectedId=00000000-0000-0000-0000-000000000000" -o 'events.json')
