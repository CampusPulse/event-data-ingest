#!/usr/bin/env python

#
# Parse stage should convert raw data into json records and store as ndjson.
#

import re
import json
import pathlib
import datetime
import re
import sys
from typing import Dict, List
from json import JSONEncoder
from dateutil import parser as dateparser
from dateutil.parser import ParserError

from icalendar import Calendar, Event
from bs4 import BeautifulSoup


# ALLOWED_NORMALIZED_COLUMNS = {"clinic", "slots", "type", "address", "hours"}


# def soupify_file(input_path: pathlib.Path) -> List[BeautifulSoup]:
#     """Opens up a provided file path, feeds it into BeautifulSoup.
#     Returns a new BeautifulSoup object for each found table
#     """
#     with open(input_path, "r") as fd:
#         return BeautifulSoup(fd, "html.parser").find_all("table")


# def find_data_rows(soup: BeautifulSoup) -> List[BeautifulSoup]:
#     """Queries the provided BeautifulSoup to find <tr> elements which are inside a <tbody>.
#     Exploring the data shows that such rows correspond to vaccine site data
#     """

#     def is_data_row(tag):
#         return tag.name == "tr" and tag.parent.name == "tbody"

#     return soup.find_all(is_data_row)


# def find_column_headings(soup: BeautifulSoup) -> List[str]:
#     """Queries the provided BeautifulSoup to find <th> elements under a <thead>.
#     Column names are normalized for later conditional parsing.
#     Returns a list of normalized column names
#     """

#     def translate(col: str) -> str:
#         """The source HTML isn't always consistent in how columns are named.
#         This function allows us to map divergent labels onto the correct label for parsing
#         """
#         translation = {"types": "type", "name": "clinic"}
#         if col in translation.keys():
#             return translation[col]
#         else:
#             return col

#     headings = [th.contents for th in soup.find_all("th") if len(th.contents) > 0]
#     normalized_cols = ["_".join(col).lower() for col in headings]
#     translated_cols = map(translate, normalized_cols)
#     return [col for col in translated_cols if col in ALLOWED_NORMALIZED_COLUMNS]


# def parse_row(row: BeautifulSoup, columns: List[str], table_id: str) -> Dict[str, str]:
#     """Takes a BeautifulSoup tag corresponding to a single row in an HTML table as input,
#     along with an ordered list of normalized column names.
#     Labels data in each row according to the position of the column names.
#     Returns a dict of labeled data, suitable for transformation into ndjson
#     """

#     def extract_appt_slot_count(appt_slots: str) -> str:
#         pattern = re.compile(r"(\d+) slots")
#         match = re.search(pattern, appt_slots)
#         return "0" if match is None else match.group(1)

#     data = [td.contents for td in row.find_all("td")]
#     assert len(data) >= len(
#         columns
#     ), "Failed to parse row, column and field mismatch! {data}, {columns}"
#     result: Dict[str, str] = {}
#     for key, value in zip(columns, data):
#         if key == "clinic":
#             # Speculatively assign the address field from the clinic name. At least one
#             # store has a blank address field but contains the address in the clinic name
#             try:
#                 clinic, _, address = tuple(value)
#                 result["clinic"] = clinic
#                 result["address"] = address
#             except ValueError:
#                 # Not every store contains the address in the clinic name
#                 result["clinic"] = value[0]
#         if key == "slots":
#             result[key] = extract_appt_slot_count(str(value[0]))
#         else:
#             if len(value) != 0:
#                 result[key] = value[0]
#     result["row_id"] = row.attrs["data-row_id"]
#     result["table_id"] = table_id
#     return result


# def removePrevious


if __name__ == "__main__":
    output_dir = pathlib.Path(sys.argv[1])
    input_dir = pathlib.Path(sys.argv[2])

    events = []

    for html in input_dir.glob("**/event_*.html"):
        if not html.is_file():
            continue
                
        filedata = html.read_text()

        soup = BeautifulSoup(filedata, features="html.parser")

        # parse details that are the same for every event
        name_attr = soup.find(attrs={'class': "field--name-title"})
        name_children = list(name_attr.children)
        name = name_children[0].get_text().strip()

        title_link = name_children[-1].get_text().strip() if len(name_children) > 1 else None

        description = soup.find(attrs={'class': "field--name-field-event-description"}).get_text().strip()

        ical_link_attr = soup.find("a", string=re.compile("\w*Add to Calendar\w*"))
        #attrs={'href': "node/*/calendar.ics"})#
        # print(ical_link_attr)
        # ical_link_attr = ical_link_attr
        ical_link = "https://rit.edu/events/" + ical_link_attr["href"]
        node_id = ical_link_attr["href"].split("/")[1]

        occurrences = []
        print(f"processing event: {name}")

        # potentially multiple event times
        for event_html in soup.find_all(attrs={'class': "paragraph--type--event-schedule"}):

            items = list(event_html.find_all("div"))
            # # debug
            # for i in range(len(items)):
            # 	txt = items[i].get_text()
            # 	txt = txt.strip()
            # 	if txt != "":
            # 		print(i, txt)

            date = items[0].get_text()
            timerange = items[1].get_text()
            is_all_day = "All Day" in timerange.strip()
            timerange = timerange.split("-")

            

            starttime = date + " " + timerange[0] if not is_all_day else None
            endtime = date + " " + timerange[1] if not is_all_day and len(timerange) >= 2 else None
           
           
            starttime = starttime if not is_all_day else date
            try:
                starttime = dateparser.parse(starttime).isoformat()
            except ParserError:
                # the parsing of the datetime failed, just include it as a string
                print(f"parsing of datetime value {starttime} failed, falling back to just including the value (its the normalizers problem now)")
                pass

            print(f"\tprocessing event occurrence starting at: {starttime}")
            endtime = endtime if not is_all_day else None
            if endtime is not None:
                try:
                    endtime = dateparser.parse(endtime).isoformat()
                except ParserError:
                    # the parsing of the datetime failed, just include it as a string
                    print(f"parsing of datetime value {starttime} failed, falling back to just including the value (its the normalizers problem now)")
                    pass
            
            

            building = items[2].get_text().strip() if len(items) >= 3 else None 
            
            room = items[3] if len(items) >= 4 else None 
            room = room.get_text().split(":")[1].strip() if room is not None else ""
            # location = building + " - " + room
            location = None #addrees
            occurrences.append({
                'location': location,
                'building': building,
                'room': room,
                'is_all_day': is_all_day,
                'starttime': starttime,
                'endtime': endtime
            })
            
        
        public = soup.find_all(string="Open to the Public")
        is_public = len(public) >= 1
        
        interp = soup.find(string="Interpreter Requested?")
        interp_status = interp.next_sibling.text if interp.next_sibling else None

        contact_name = soup.find(attrs={'class': "field--name-field-contact-name"})
        contact_name = contact_name.get_text() if contact_name else None

        contact_email = soup.find(attrs={'class': "field--name-field-contact-email"})
        contact_email = contact_email.get_text() if contact_email else None

        contact_phone = soup.find(attrs={'class': "field--name-field-contact-phone"})
        contact_phone = contact_phone.get_text() if contact_phone else None



        topics = soup.find(attrs={'class': "field--name-field-event-general-topics"})
        topics = [e.string for e in topics.find_all(attrs={'class': "field__item"})] if topics else []


    
        # e = Event()
        # e.name = name
        # e.description = description
        # e.begin = tz.localize(starttime)
        # e.end = tz.localize(endtime)
        # e.location = building
        # events.append(e)

        e = {}

        e["name"] = name
        e["title_link"] = title_link
        e["description"] = description
        e["ical_link"] = ical_link
        e["node_id"] = node_id
        # e["begin"] = tz.localize(starttime)
        # e["end"] = tz.localize(endtime)
        e["occurrences"] = occurrences
        # e["location"] = building
        e["is_public"] = is_public
        e["interp"] = interp
        e["contact_name"] = contact_name
        e["contact_email"] = contact_email
        e["contact_phone"] = contact_phone
        e["topics"] = topics

        events.append(e)

    output = "\n".join(json.dumps(event) for event in events)
    outpath = output_dir / "events.parsed.ndjson"
    with open(outpath, "w") as fd:
        fd.write(output)