#!/usr/bin/env python


#
# Normalize stage should transform parsed json records into the normalized schema
#

import datetime
import json
import os
import pathlib
import sys
from typing import List, Optional, OrderedDict

import pydantic
import us
import usaddress
import campuspulse_event_ingest_schema  as schema
from dateutil import parser as dateparser
from dateutil.tz import gettz

from event_data_ingest.utils.log import getLogger
# from event_data_ingest.utils.normalize import (
#     normalize_address,
#     normalize_phone,
#     normalize_zip,
#     parse_address,
# )

logger = getLogger(__file__)


SOURCE_NAME = "rit_ehouse"


class CustomBailError(Exception):
    pass


# def _get_availability(site: dict) -> schema.Availability:
#     appt_only = site["attributes"]["appt_only"]

#     appt_options = {
#         "Yes": True,
#         "No": False,
#         "Vax only": True,
#         "Test only": False,
#     }

#     avail = try_lookup(appt_options, appt_only, None, name="availability lookup")

#     if avail is not None:
#         return schema.Availability(appointments=avail)
#     # there seems to be no walk-in data unless you want to parse "drive_in" = yes and "vehiche_required" = no into a "walk-in = yes"

#     return None


def _get_id(site: dict) -> str:
    data_id = site["UID"]

    return f"{SOURCE_NAME}_{data_id}"


# def _get_contacts(site: dict) -> Optional[List[schema.Contact]]:
#     contacts = []
#     if site["attributes"]["phone"]:
#         for phone in normalize_phone(site["attributes"]["phone"]):
#             contacts.append(phone)

#     # if site["attributes"]["publicEmail"]:
#     #     contacts.append(schema.Contact(email=site["attributes"]["publicEmail"]))

#     # there are multiple urls, vaccine, agency, health dept. etc
#     if site["attributes"]["vaccine_url"]:
#         url = site["attributes"]["vaccine_url"]
#         url = sanitize_url(url)
#         if url:
#             contacts.append(schema.Contact(website=url))

#     if len(contacts) > 0:
#         return contacts

#     return None


def sanitize_url(url):
    url = url.strip()
    url = url.replace("#", "")
    url = url.replace("\\", "/")  # thanks windows
    url = url if url.startswith("http") else "https://" + url
    if len(url.split(" ")) == 1:
        return url
    return None


def _get_notes(site: dict) -> Optional[List[str]]:
    notes = []
    if site["attributes"]["Instructions"]:
        notes.append(site["attributes"]["Instructions"])

    if site.get("opening_hours_notes"):
        notes.append(site["opening_hours_notes"])

    if comments := site.get("comments"):
        notes.append(comments)

    if notes != []:
        return notes

    return None


def _get_opening_hours(site):
    oh = site.get("operhours")
    if oh:
        try:
            return OpeningHours.parse(oh).json()
        except Exception:
            # store the notes back in the dict so the notes function can grab it later
            site["opening_hours_notes"] = "Hours: " + oh
    else:
        return None


def _get_active(site: dict) -> Optional[bool]:
    # end date may be important to check to determine if the site is historical or current. see docs on these fields at https://docs.google.com/document/d/1xqZDHtkNHfelez2Rm3mLAKTwz7gjCAMJaMKK_RxK8F8/edit#
    # these fields are notcurrently  supported by the VTS schema

    status = site["attributes"].get("status")

    status_options = {
        "Open": True,
        "Closed": False,
        "Testing Restricted": True,
        "Scheduled to Open": False,
        "Temporarily Closed": False,
    }

    return try_lookup(status_options, status, None, name="active status lookup")


# def _get_access(site: dict) -> Optional[List[str]]:
#     drive = site["attributes"].get("drive_through")
#     drive_bool = drive is not None and drive == "Yes"

#     # walk = site["attributes"].get("drive_through")
#     # walk_bool = drive is not None

#     wheelchair = site["attributes"].get("Wheelchair_Accessible")

#     wheelchair_options = {
#         "Yes": "yes",
#         "Partially": "partial",
#         "Unknown": "no",
#         "Not Applicable": "no",
#         "NA": "no",
#     }
#     wheelchair_bool = try_lookup(
#         wheelchair_options, wheelchair, "no", name="wheelchair access"
#     )

#     return schema.Access(drive=drive_bool, wheelchair=wheelchair_bool)


def try_lookup(mapping, value, default, name=None):
    if value is None:
        return default

    try:
        return mapping[value]
    except KeyError as e:
        name = " for " + name or ""
        logger.warn("value not present in lookup table%s: %s", name, e)

        return default


def _get_published_at(site: dict) -> Optional[str]:
    date_with_millis = site["attributes"]["EditDate"]
    if date_with_millis:
        date = datetime.datetime.fromtimestamp(date_with_millis / 1000)  # Drop millis
        return date.isoformat()

    return None


# def _get_opening_dates(site: dict) -> Optional[List[schema.OpenDate]]:
#     start_date = site["attributes"].get("start_date")

#     end_date = site["attributes"].get("end_date")

#     if start_date:
#         start_date = datetime.datetime.fromtimestamp(start_date / 1000)

#     if end_date:
#         end_date = datetime.datetime.fromtimestamp(end_date / 1000)

#     if start_date and end_date and start_date > end_date:
#         return None

#     if start_date or end_date:
#         return [schema.OpenDate(opens=start_date, closes=end_date)]
#     else:
#         return None


def try_get_list(lis, index, default=None):
    if lis is None:
        return default

    try:
        value = lis[index]
        if value == "none":
            logger.warn("saw none value")
        return value
    except IndexError:
        return default


# def try_get_lat_long(site):
#     location = None
#     try:
#         location = schema.LatLng(
#             latitude=site["geometry"]["y"],
#             longitude=site["geometry"]["x"],
#         )
#     except KeyError:
#         pass

#     return location


def normalize_state_name(name: str) -> str:

    if name is None:
        return name

    name = name.strip()
    name = name.replace(".", "")
    name = name.replace("'", "")

    # capitalize the first letter of each word in cases where a state name is provided
    spl = name.split(" ")
    if len(spl) > 1:
        " ".join([word.capitalize() for word in spl])
    else:
        name = name.lower().capitalize()

    lookup = us.states.lookup(name)
    if lookup:
        return lookup.abbr
    else:
        return name.upper()


def apply_address_fixups(address: OrderedDict[str, str]) -> OrderedDict[str, str]:

    if "PlaceName" in address and "StateName" in address:
        problem_dakotas = [
            "Valley City, North",
            "Williston North",
            "Belle Fourche, South",
        ]
        if address["PlaceName"] in problem_dakotas and address["StateName"] == "Dakota":
            pl_old = address["PlaceName"]
            address["PlaceName"] = pl_old[:-5].strip()
            address["StateName"] = pl_old[-5:] + " Dakota"

    if "StateName" in address:
        state = address["StateName"]

        if state == "ND North Dakota":
            state = "North Dakota"
        elif state == "Mich.":
            state = "Michigan"
        elif state in ["SR", "US", "HEIGHTS"]:
            # raise CustomBailError()
            del address["StateName"]
            state = None
        elif state == "GL":
            state = "FL"

        if state in ["Bay Arkansas", "Palestine Arkansas"]:
            spl = state.split(" ")
            state = spl[1]
            address["PlaceName"] = (
                address.get("PlaceName") or "" + " " + spl[0]
            ).strip()

        address["StateName"] = normalize_state_name(state)

        if address["StateName"] and len(address["StateName"]) == 1:
            del address["StateName"]

        if address.get("StateName") in [
            "ANCHORAGE",
            "LAGOON",
            "C2",
            "IN SPRINGFIELD",
            "BAY",
            "JUNCTION",
            "JERSEY",
            "CAROLINA",
            "FE",
            "MEXICO",
            "OAKS",
            "GUAYAMA",
            "ISABELA",
            "HATILLO",
            "BAYAMÓN",
            "CAGUAS",
            "FAJARDO",
            "PONCE",
            "MAYAGÜEZ",
            "ISLANDS",
            "LIMA",
            "CLAYTON",
        ]:

            address["PlaceName"] = (
                address.get("PlaceName") or "" + " " + address["StateName"].lower()
            ).strip()

            del address["StateName"]

        if address.get("StateName") == "ALA":
            address["StateName"] = "AL"

        if address.get("StateName") == "PA15068":
            address["StateName"] = "PA"
            address["ZipCode"] = "15068"

    if "ZipCode" in address:
        normalzip = normalize_zip(address["ZipCode"])
        if normalzip:
            address["ZipCode"] = normalzip
        else:
            del address["ZipCode"]

    return address


def _parse_location(site):
    try:
        loc = site["LOCATION"]
    except Exception as e: 
        logger.info("Skipping parsing for one record due to exception")
        logger.warning(
            "An error occurred while parsing the address for ehouse record "
            + site["UID"]
            + ": "
            + str(e)
        )
        return None

    return schema.Location(
        street=loc,
        # city= city,
        # state=state
    )

# def _parse_time(site,)

def _get_normalized_event(site: dict, timestamp: str) -> schema.NormalizedEvent:
    logger.warning(site)
    return schema.NormalizedEvent(
        identifier = _get_id(site),#: str
        title = site.get("SUMMARY"),#: Optional[str]
        location = _parse_location(site),#: Optional[Location]
        # date = ,#: Optional[StringDate]
        # isAllDay = site.get("allDay"),#: Optional[bool]
        start = dateparser.parse(site.get("DTSTART")).replace(tzinfo=None),#: Optional[StringTime]
        end = dateparser.parse(site.get("DTEND")).replace(tzinfo=None) if site.get("DTEND") else None,#: Optional[StringTime]
        # duration = ,#: Optional[StringTime]
        description = site.get("DESCRIPTION"),#: Optional[str]
        # host = ,#: Optional[str]
        is_public = True,#: bool
        source = schema.EventSource(
            source_id = site.get("id"),
            # source_link: Optional[str]
            # submitter: Optional[str]
            processed_at =  timestamp
        ),#: EventSource
    )



def json_serial(obj):
    """JSON serializer for objects not serializable by default json code"""

    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    raise TypeError ("Type %s not serializable" % type(obj))


output_dir = pathlib.Path(sys.argv[1])
input_dir = pathlib.Path(sys.argv[2])

json_filepaths = input_dir.glob("*.ndjson")

parsed_at_timestamp = datetime.datetime.utcnow().isoformat()

for in_filepath in json_filepaths:
    filename, _ = os.path.splitext(in_filepath.name)
    out_filepath = output_dir / f"{filename}.normalized.ndjson"

    logger.info(
        "normalizing %s => %s",
        in_filepath,
        out_filepath,
    )

    with in_filepath.open() as fin:
        with out_filepath.open("w") as fout:
            for site_json in fin:
                parsed_site = json.loads(site_json)

                normalized_site = _get_normalized_event(
                    parsed_site, parsed_at_timestamp
                )

                print(normalized_site)
                json.dump(normalized_site.dict(), fout, default=json_serial)
                fout.write("\n")
