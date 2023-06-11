#!/usr/bin/env python

#
# Parse stage should convert raw data into json records and store as ndjson.
#

import json
import pathlib
import re
import sys
from typing import Dict, List

from bs4 import BeautifulSoup



def soupify_file(input_path: pathlib.Path) -> List[BeautifulSoup]:
    """Opens up a provided file path, feeds it into BeautifulSoup.
    Returns a new BeautifulSoup object for each found table
    """
    with open(input_path, "r") as fd:
        return BeautifulSoup(fd, "html.parser")


def extract_room_info(page: BeautifulSoup) -> Dict[str, str]:
    """Takes a BeautifulSoup tag corresponding to a page as input,
    Returns a dict of labeled data, suitable for transformation into ndjson
    """
    result: Dict[str, str] = {}


    roomSizes = page.find_all("div",class_="field--name-field-room-size")
    singleSemCosts = page.find_all("div",class_="field--name-field-per-semester-per-person")
    twoSemCosts = page.find_all("div",class_="field--name-field-per-2-semesters-per-person")
    roomSizeArr = []
    singSemCostArr = []
    twoSemCostArr = []
    for roomSize in roomSizes:
        roomSizeArr.append(roomSize.text)
    for singleSemCost in singleSemCosts:
        singSemCostArr.append(singleSemCost.text)
    for twoSemCost in twoSemCosts:
        twoSemCostArr.append(twoSemCost.text)

    result["rooms"] = []

    for i in range(len(roomSizeArr)):
        roomStyle = {}
        roomStyle["size"](roomSizeArr[i])
        roomStyle["cost"] = {
            "semster": singSemCostArr[i],
            "year": twoSemCostArr[i],
            "summer":""
        }
        result["rooms"].append(roomStyle)

    return result

if __name__ == "__main__":
    output_dir = pathlib.Path(sys.argv[1])
    input_dir = pathlib.Path(sys.argv[2])

    for html in input_dir.glob("**/*.html"):
        if not html.is_file():
            continue
        data = []
        
        for result in soupify_file(html).find_all("div", class_="view-rates"):

            data.extend(
                [
                    extract_room_info(result)
                ]
            )


        output = "\n".join(json.dumps(item) for item in data)
        outpath = output_dir / (html.with_suffix(".parsed.ndjson").name)
        with open(outpath, "w") as fd:
            fd.write(output)
