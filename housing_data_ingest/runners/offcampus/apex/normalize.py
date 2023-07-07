#!/usr/bin/env python


#
# Normalize stage should transform parsed json records into VaccinateCA apartment
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
from rit_housing_data_schema import apartment
from dateutil import parser

from housing_data_ingest.utils.log import getLogger
from housing_data_ingest.utils.normalize import (
    normalize_address,
    normalize_phone,
    normalize_zip,
    parse_address,
)

logger = getLogger(__file__)


SOURCE_NAME = "apex"


class CustomBailError(Exception):
    pass


# def _get_availability(data: dict) -> apartment.Availability:
#     appt_only = data["attributes"]["appt_only"]

#     appt_options = {
#         "Yes": True,
#         "No": False,
#         "Vax only": True,
#         "Test only": False,
#     }

#     avail = try_lookup(appt_options, appt_only, None, name="availability lookup")

#     if avail is not None:
#         return apartment.Availability(appointments=avail)
#     # there seems to be no walk-in data unless you want to parse "drive_in" = yes and "vehiche_required" = no into a "walk-in = yes"

#     return None


def _get_id(data: dict) -> str:
    return f"{data['_id']}"


def _get_contacts(data: dict) -> Optional[List[apartment.Contact]]:
    contacts = []
    if data["attributes"]["phone"]:
        for phone in normalize_phone(data["attributes"]["phone"]):
            contacts.append(phone)

    # if data["attributes"]["publicEmail"]:
    #     contacts.append(apartment.Contact(email=data["attributes"]["publicEmail"]))

    # there are multiple urls, vaccine, agency, health dept. etc
    if data["attributes"]["vaccine_url"]:
        url = data["attributes"]["vaccine_url"]
        url = sanitize_url(url)
        if url:
            contacts.append(apartment.Contact(webdata=url))

    if len(contacts) > 0:
        return contacts

    return None


def sanitize_url(url):
    url = url.strip()
    url = url.replace("#", "")
    url = url.replace("\\", "/")  # thanks windows
    url = url if url.startswith("http") else "https://" + url
    if len(url.split(" ")) == 1:
        return url
    return None


def _get_description(data: dict) -> Optional[List[str]]:
    notes = []
    if data["attributes"]["Instructions"]:
        notes.append(data["attributes"]["Instructions"])

    if data.get("opening_hours_notes"):
        notes.append(data["opening_hours_notes"])

    if comments := data.get("comments"):
        notes.append(comments)

    if notes != []:
        return notes

    return None


def _get_active(data: dict) -> Optional[bool]:
    # end date may be important to check to determine if the data is historical or current. see docs on these fields at https://docs.google.com/document/d/1xqZDHtkNHfelez2Rm3mLAKTwz7gjCAMJaMKK_RxK8F8/edit#
    # these fields are notcurrently  supported by the VTS apartment

    status = data["attributes"].get("status")

    status_options = {
        "Open": True,
        "Closed": False,
        "Testing Restricted": True,
        "Scheduled to Open": False,
        "Temporarily Closed": False,
    }

    return try_lookup(status_options, status, None, name="active status lookup")


def _get_access(data: dict) -> Optional[List[str]]:
    drive = data["attributes"].get("drive_through")
    drive_bool = drive is not None and drive == "Yes"

    # walk = data["attributes"].get("drive_through")
    # walk_bool = drive is not None

    wheelchair = data["attributes"].get("Wheelchair_Accessible")

    wheelchair_options = {
        "Yes": "yes",
        "Partially": "partial",
        "Unknown": "no",
        "Not Applicable": "no",
        "NA": "no",
    }
    wheelchair_bool = try_lookup(
        wheelchair_options, wheelchair, "no", name="wheelchair access"
    )

    return apartment.Access(drive=drive_bool, wheelchair=wheelchair_bool)


def try_lookup(mapping, value, default, name=None):
    if value is None:
        return default

    try:
        return mapping[value]
    except KeyError as e:
        name = " for " + name or ""
        logger.warn("value not present in lookup table%s: %s", name, e)

        return default


def _get_updated_at(data: dict) -> Optional[str]:
    return data.get("updated_at")


def _get_opening_dates(data: dict) -> Optional[List[apartment.OpenDate]]:
    start_date = data["attributes"].get("start_date")

    end_date = data["attributes"].get("end_date")

    if start_date:
        start_date = datetime.datetime.fromtimestamp(start_date / 1000)

    if end_date:
        end_date = datetime.datetime.fromtimestamp(end_date / 1000)

    if start_date and end_date and start_date > end_date:
        return None

    if start_date or end_date:
        return [apartment.OpenDate(opens=start_date, closes=end_date)]
    else:
        return None


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


def _get_address(data):
    try:
        parsed = parse_address(data["attributes"]["fulladdr"])

        parsed = apply_address_fixups(parsed)

        normalized = normalize_address(parsed)

        return normalized
    except (
        usaddress.RepeatedLabelError,
        CustomBailError,
        pydantic.error_wrappers.ValidationError,
    ) as e:
        logger.info("Skipping parsing for one record due to exception")
        logger.warning(
            "An error occurred while parsing the address for GISCorps record "
            + data["attributes"]["GlobalID"]
            + ": "
            + str(e)
        )
        return None


def _parse_amenity(amenity: dict) -> Optional[List[apartment.Amenity]]:
    return apartment.Amenity(
        name=amenity["name"],
    )


def _get_unit_type(model: dict) -> Optional[apartment.UnitType]:

    if model["disabled"] is False:

        modelname = None
        modelid=model.get("id")
        try:
            modelname = model.get("label") or model["images"][0]["title"]
        except KeyError as e:
            logger.info("keyerror while processing unit - falling back to other sources of potentially less reliable names for model id " + modelid)

        rent = model.get("rent")
        images = model.get("images")

        return apartment.UnitType(
            name=modelname,
            # description="1 bedroom apt",
            id=modelid,
            # shared=False,
            bedroomCount=model.get("beds"),
            bathroomCount=model.get("baths"),
            floorplanUrl=f'https://assets.myrazz.com/{images[0].get("uuid")}' if images else None, #TODO: get floorplan image,
            rent=apartment.RentCost(
                minCost=rent["min"] if rent else None,
                maxCost=rent["min"] if rent else None,
                notes=model.get("rentLabel"),
            ),
            # appliances=apartment.Appliances(
            #     washingMachine=False,
            #     dryer=False,
            #     oven=False,
            #     stove=False,
            #     ovenAsRange=False,
            #     dishwasher=False,
            #     refrigerator=False,
            #     microwave=False,
            # ),
            # amenities=[apartment.Amenity(name="AC", description="it barely works")],
            # utilitiesCost=apartment.UtilityCosts(
            #     electric=90,
            #     water=90,
            #     gas=90,
            #     sewer=90,
            #     internet=90,
            # ),
        )


# the apartment for the incoming data is documented at https://docs.google.com/document/d/1xqZDHtkNHfelez2Rm3mLAKTwz7gjCAMJaMKK_RxK8F8/edit#
def _get_normalized_apartmentcomplex(
    data: dict, timestamp: str
) -> apartment.NormalizedApartmentComplex:

    trimmedData = data
    del trimmedData["units"]

    return apartment.NormalizedApartmentComplex(
        id=f"{SOURCE_NAME}:{_get_id(data)}",
        name=SOURCE_NAME,
        # address=_get_address(data),
        # contact=_get_contacts(data),
        # opening_dates=_get_opening_dates(data),
        # opening_hours=_get_opening_hours(data),
        # availability=_get_availability(data),
        # access=_get_access(data),
        # links=None,
        # description=_get_description(data),
        # active=_get_active(data),
        onRITCampus=False,
        # renewable=False,
        # subletPolicy="",
        # reletPolicy="",
        # imageUrl="https://4.bp.blogspot.com/-2llfvEbN9O8/T8zrEtTLkCI/AAAAAAAAMyc/zP4uPLwaQss/s1600/these-funny-cats-001-031.jpg",
        amenities=[_parse_amenity(a) for a in data["amenities"]],
        unitTypes=[_get_unit_type(u) for u in data["models"]],
        source=apartment.Source(
            source=SOURCE_NAME,
            id=_get_id(data),
            fetched_from_uri="https://www.lifeatapex.com/api/v1/content",  # noqa: E501
            fetched_at=timestamp,
            published_at=_get_updated_at(data),
            data=trimmedData,
        ),
    )


# apartment.NormalizedApartmentComplex(
#         id="source:id",
#         name="name",
#         address=apartment.Address(
#             street1="1991 Mountain Boulevard",
#             street2="#1",
#             city="Oakland",
#             state="CA",
#             zip="94611",
#         ),
#         contact=[
#             apartment.Contact(
#                 contact_type="booking",
#                 phone="(916) 445-2841",
#             )
#         ],
#         opening_dates=[
#             apartment.OpenDate(
#                 opens="2021-04-01",
#                 closes="2021-04-01",
#             ),
#         ],
#         opening_hours=[
#             apartment.OpenHour(
#                 day="monday",
#                 opens="08:00",
#                 closes="14:00",
#             ),
#         ],
#         availability=apartment.Availability(
#             drop_in=False,
#             appointments=True,
#         ),
#         access=apartment.Access(
#             walk=True,
#             drive=False,
#             wheelchair="partial",
#         ),
#         links=["https://www.google.com"],
#         active=True,
#         source=apartment.Source(
#             source="source",
#             id="id",
#             fetched_from_uri="https://example.org",
#             fetched_at="2020-04-04T04:04:04.4444",
#             published_at="2020-04-04T04:04:04.4444",
#             data={"id": "id"},
#         ),
#
#     )

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
            for data_json in fin:
                parsed_data = json.loads(data_json)

                normalized_data = _get_normalized_apartmentcomplex(
                    parsed_data, parsed_at_timestamp
                )

                json.dump(normalized_data.dict(), fout)
                fout.write("\n")
