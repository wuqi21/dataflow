import requests
from loguru import logger
import pandas as pd
import json
import sys
import pathlib

user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"


cookies = {
        "_ga": "GA1.1.575776775.1746755352",
        "_ga_F4Q7EX1K95": "GS2.1.s1749177231$o14$g1$t1749177238$j53$l0$h0",
        "_ga_CSLL4ZEK4L": "GS2.1.s1749177231$o17$g1$t1749177241$j50$l0$h0",
    }
keys = 'drug-loaded AND microspheres'

outdir = sys.argv[1]

pathlib.Path(outdir).mkdir(parents=True,exist_ok=True)

def get_session():
    logger.info("[session] start getting session")
    headers = {
        "accept": "*/*",
        "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "content-type": "application/json; charset=utf-8",
        "origin": "https://ppubs.uspto.gov",
        # "priority": "u=1, i",
        "referer": "https://ppubs.uspto.gov/pubwebapp/static/pages/ppubsbasic.html",
        "sec-ch-ua": '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": user_agent,
        "x-access-token": "null",
    }

    url = "https://ppubs.uspto.gov/api/users/me/session"
    response = requests.post(url, headers=headers, cookies=cookies, data="-1")
    x_access_token = response.headers.get("x-access-token")
    if x_access_token:
        logger.success(
            "[session] get x-access-token success. x-access-token: {}".format(
                x_access_token
            )
        )
        return x_access_token
    raise Exception("Failed to get x-access-token")


def search_uspto():
    logger.info("[search] start searching uspto")
    headers = {
        "accept": "application/json",
        "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        "content-type": "application/json",
        "origin": "https://ppubs.uspto.gov",
        "priority": "u=1, i",
        "referer": "https://ppubs.uspto.gov/pubwebapp/static/pages/ppubsbasic.html",
        "sec-ch-ua": '"Chromium";v="136", "Google Chrome";v="136", "Not.A/Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": user_agent,
        "x-access-token": get_session(),
    }

    data = {
        "cursorMarker": "*",
        "databaseFilters": [
            {"databaseName": "USPAT"},
            {"databaseName": "US-PGPUB"},
            {"databaseName": "USOCR"},
        ],
        "fields": [
            "documentId",
            "patentNumber",
            "title",
            "datePublished",
            "inventors",
            "pageCount",
            "type",
        ],
        "op": "AND",
        "pageSize": 999999,
        "q": keys,
        "searchType": 0,
        "sort": "date_publ desc",
    }

    url = "https://ppubs.uspto.gov/api/searches/generic"
    response = requests.post(url, headers=headers, cookies=cookies, json=data)
    return response.json()


if __name__ == "__main__":
    response = search_uspto()
    # 将响应保存为JSON文件
    with open(f"{outdir}/search_results.json", "w", encoding="utf-8") as f:
        json.dump(response, f, ensure_ascii=False, indent=4)
    logger.info("[search] 已将搜索结果保存到 uspto_response.json")
    # 将JSON数据转换为DataFrame
    df = pd.DataFrame(response["docs"])

    # 保存为CSV文件
    df.to_csv(f"{outdir}/search_results.csv", index=False, encoding="utf-8")
    logger.info("[search] 已将搜索结果保存到 uspto_results.csv")
    # print(get_session())