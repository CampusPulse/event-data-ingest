#!/usr/bin/env python

#
# Parse stage should convert raw data into json records and store as ndjson.
#


import json
import pathlib
import datetime
import re
import sys
from typing import Dict, List
from json import JSONEncoder

from icalendar import Calendar, Event

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

    for ics in input_dir.glob("**/*.ics"):
        if not ics.is_file():
            continue
                
        filedata = ics.read_text()

        class ICalendarEncoder(JSONEncoder):
            def default(self, obj, markers=None):

                try:
                    if obj.__module__.startswith("icalendar.prop"):#"ics"):
                        return (obj.to_ical())
                except AttributeError:
                    pass

                if isinstance(obj, datetime.datetime):
                    return (obj.now().strftime('%Y-%m-%dT%H:%M:%S'))

                if isinstance(obj, bytes):
                    return (obj.decode("utf-8"))

                return JSONEncoder.default(self,obj)    


        cal = Calendar.from_ical(filedata)

        events = list(cal.walk(name="VEVENT"))

        for event in events:
            for c in event["CATEGORIES"]:
                cg_category_type = c.params["X-CG-CATEGORY"]
                event[cg_category_type] = c.cats
            del event["CATEGORIES"]

        output = "\n".join(json.dumps(event, cls=ICalendarEncoder) for event in events)
        outpath = output_dir / (ics.with_suffix(".parsed.ndjson").name)
        with open(outpath, "w") as fd:
            fd.write(output)
