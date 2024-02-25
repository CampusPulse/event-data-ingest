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


outdir = Path(output_dir)


while True:
	print(f"getting event page {page}")
	params = urllib.parse.urlencode({"page": page})
	url = f"{base_url.geturl()}?{params}"
	response = requests.get(url, allow_redirects=False, headers=headers)
	content = response.text

	with open(outdir / f"page_{page}.html", "w") as f:
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


soup = BeautifulSoup(output, "html.parser")

links = soup.find_all("a")
print(links)
links = [a.get('href') for a in links]

for link in links:
	print(f"getting event {link}")
	if not link.startswith("/events"):
		print(f"link {link} isnt in the right format, skipping")
		# this basically happens for external links, including those to the /croatia/events page
		continue
	eventname = link.split('/')[-1]

	outpath = outdir / f"event_{eventname}.html"

	if outpath.exists():
		print("\tskipping already scraped event")
		continue
	url = f"{base_url.geturl()}{link}"
	response = requests.get(url, allow_redirects=True, headers=headers)
	content = response.text
	
	with open(outpath, "w") as f:
		f.write(content)
