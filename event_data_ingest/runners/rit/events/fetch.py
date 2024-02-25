#!/usr/bin/env python3

import os
from pathlib import Path
import sys
import urllib.parse

import requests
import yaml
from bs4 import BeautifulSoup

from event_data_ingest.utils.log import getLogger

logger = getLogger(__file__)

output_dir = sys.argv[1]


base_url = urllib.parse.urlparse("https://www.rit.edu/events/")
headers = {}
extra_params = {}
page = 0
output = ""


pages_outdir = Path(os.path.join(output_dir, f"pages"))
pages_outdir.mkdir()


while True:
	
	params = urllib.parse.urlencode({"page": page})
	url = f"{base_url.geturl()}?{params}"
	response = requests.get(url, allow_redirects=False, headers=headers)
	content = response.text

	with open(pages_outdir / "{page}.html", "w") as f:
		f.write(content)

	soup = BeautifulSoup(content, "html.parser")

	upcoming = soup.find(id="views-bootstrap-event-display-upcoming-events")
	# print(upcoming.text)
	output += str(upcoming)

	current_page = int(list(soup.find('a', title="Current page").children)[-1])
	if current_page != (page + 1):
		break
	page += 1


with open(os.path.join(output_dir, f"upcomingevents-combined.html"), "w") as f:
	f.write(output)
