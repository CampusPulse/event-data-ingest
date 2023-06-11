import requests
from bs4 import BeautifulSoup

URL = "https://www.rit.edu/housing/residence-halls"
page = requests.get(URL)

soup = BeautifulSoup(page.content, "html.parser")

results = soup.find_all("div", class_="view-rates")
for result in results:
    roomSizes = result.find_all("div",class_="field--name-field-room-size")
    singleSemCosts = result.find_all("div",class_="field--name-field-per-semester-per-person")
    twoSemCosts = result.find_all("div",class_="field--name-field-per-2-semesters-per-person")
    roomSizeArr = []
    singSemCostArr = []
    twoSemCostArr = []
    for roomSize in roomSizes:
        roomSizeArr.append(roomSize.text)
    for singleSemCost in singleSemCosts:
        singSemCostArr.append(singleSemCost.text)
    for twoSemCost in twoSemCosts:
        twoSemCostArr.append(twoSemCost.text)

    for i in range(len(roomSizeArr)):
        print(roomSizeArr[i])
        print(singSemCostArr[i])
        print(twoSemCostArr[i])