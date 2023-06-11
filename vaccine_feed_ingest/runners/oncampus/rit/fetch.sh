#!/usr/bin/env bash

set -Eeuo pipefail

output_dir=""

if [ -n "${1}" ]; then
    output_dir="${1}"
else
    echo "Must pass an output_dir as first argument"
fi

(cd "$output_dir" && curl --silent "https://www.rit.edu/housing/rates" -o 'rates.html')

(cd "$output_dir" && curl --silent "https://www.rit.edu/housing/global-village" -o 'global-village.html')
(cd "$output_dir" && curl --silent "https://www.rit.edu/housing/riverknoll" -o 'riverknoll.html')
(cd "$output_dir" && curl --silent "https://www.rit.edu/housing/perkins-green" -o 'perkins-green.html')
(cd "$output_dir" && curl --silent "https://www.rit.edu/housing/greek-circle" -o 'greek-circle.html')
(cd "$output_dir" && curl --silent "https://www.rit.edu/housing/rit-inn-conference-center" -o 'rit-inn-conference-center.html')
(cd "$output_dir" && curl --silent "https://www.rit.edu/housing/175-jefferson-road" -o '175-jefferson-road.html')