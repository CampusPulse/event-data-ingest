#!/usr/bin/env bash

set -Eeuo pipefail

output_dir=""

if [ -n "${1}" ]; then
    output_dir="${1}"
else
    echo "Must pass an output_dir as first argument"
fi

(cd "$output_dir" && curl 'https://www.livethehill.com/Apartments/module/student_property_info/action/view_floorplans/property%5Bid%5D/803168/' --compressed -H 'User-Agent: Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/114.0' -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8' -H 'Accept-Language: en-US,en;q=0.5' -H 'Accept-Encoding: gzip, deflate, br' -H 'DNT: 1' -H 'Alt-Used: www.livethehill.com' -H 'Connection: keep-alive' -H 'Cookie: PSI_SESSION_PP=PP-547509187b6b2f3fd7606a2928eb1f99; prospect_portal[website_template_id]=719; ie_warning=1; show_splash_image_803168=1; property[id]=803168; floorplan_page_onload_layout_type=stacked; is_show_filter=0; __cf_bm=4QiTyE4DwrYJJqKwis63bySq8QQ4PefkrKk5DFvzCJs-1686507776-0-AXmhi6UHyEaV2d3886cntqwU0gUPfKeC2Ncenmsp0tr54zBW780gr/qOde5ypLvYB8GfUu+P1aboWb6eSjVNWHE=; PRIVACY_SETTINGS_V1=%7B%221%22%3A%7B%22enabled_all%22%3Atrue%2C%22is_user_defined%22%3Atrue%7D%7D; move_in_date=01%2F27%2F2020; lease_start_window_id=69372; __cf_bm=gEqe4hTmJ.rXQXU7wDEh1rqAkxo.pHD2llsy4iDMTyY-1686508786-0-AdOdmF/fB8ELEJvuSZd/2cveIPDH2SygTyWN0/AH0gSMg2WrZW2gvHmtg4Ye8jvpTGLbJt/j0fOXtO+hCYVLEPU=' -H 'Upgrade-Insecure-Requests: 1' -H 'Sec-Fetch-Dest: document' -H 'Sec-Fetch-Mode: navigate' -H 'Sec-Fetch-Site: cross-site' -H 'Sec-GPC: 1' -H 'Pragma: no-cache' -H 'Cache-Control: no-cache' -H 'TE: trailers' -o 'rates-floorplans.html') # need to escape the [id] in the URL or it makes curl mad. The hill also requires a user agent

(cd "$output_dir" && curl --silent "https://www.livethehill.com/rochester/the-hill-at-rochester/amenities/" -o 'amenities.html')


