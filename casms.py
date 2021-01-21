#!/usr/bin/env python3
#
#
#
import os
import sys
import censys
import requests as req
import argparse as ap


def main():
    global api
    global msg_icons

    # Fetching Censys Search API credentials
    if "CENSYS_API_UID" in os.environ:
        api["uid"] = os.getenv("CENSYS_API_UID")

    if "CENSYS_API_SECRET" in os.environ:
        api["secret"] = os.getenv("CENSYS_API_SECRET")

    if "CENSYS_API_ALT_URL" in os.environ:
        api["url"] = os.getenv("CENSYS_API_ALT_URL")

    # Fetching Censys ASM API credentials
    if "CENSYS_ASM_API_KEY" in os.environ:
        api["asm_key"] = os.getenv("CENSYS_ASM_API_KEY")

    if "CENSYS_ASM_API_ALT_URL" in os.environ:
        api["asm_url"] = os.getenv("CENSYS_ASM_API_ALT_URL")
    
    parser = ap.ArgumentParser(description="Censys ASM Search requires both reqular Censys search API credentials and an Censys ASM API key to work properly. To set the credentials please refer to the README.md")

    # API configuration arguments
    parser.add_argument("--API-URL", type=str, help="WARNING: Do not alter the Censys API URL unless you know what you are doing!")
    parser.add_argument("--ASM-API-URL", type=str, help="WARNING: Do not alter the Censys ASM API URL unless you know what you are doing!")
    parser.add_argument("--API-CHECK", action="store_true", help="Review your API settings")

    # Search related arguments
    parser.add_argument("-q", "--query", type=str, help="Query string to search using the Censys Search platform, search queries can also be combined " \
            "with the ASM parameters for searching in private assets. For further documentation on censys search: https://censys.io/ipv4/help?q=&")
    parser.add_argument("-f", "--filter-tags", nargs="*", type=str, default=None, help="Search filter to only tagged assets")
    
    args = parser.parse_args()

    # Make sure API is updated first if any updates are passed!
    if args.API_URL is not None:
        api["url"] = args.API_URL

    if args.ASM_API_URL is not None:
        api["asm_url"] = args.ASM_API_URL

    # Running default API location settings unless API override is enabled
    if api["url"] is None:
        api["url"] = "https://censys.io/api/v1"
    else:
        print(msg_icons["warn"], "WARNING! you are running your queries through an alternate API location which is generally not recommended!")

    if api["asm_url"] is None:
        api["asm_url"] = "https://app.censys.io/api/v1"
    else:
        print(msg_icons["warn"], "WARNING! you are running your queries through an alternate API location which is generally not recommended!")

    if args.API_CHECK:
        _output_api_config()
    else:
        print(msg_icons["list"], "Checking API credentials,", end=" ")

        if None not in [api["uid"], api["secret"], api["asm_key"]]:
            print("OK")
        else:
            print("NOT OK!")
            print(msg_icons["err"], "Please add API credentials, -h for help")
    
    if args.query:
        search(query=args.query, asset_filter=args.filter_tags)


def _output_api_config():
    global api
    global msg_icons

    print("""{} CURRENT CENSYS API SETTINGS:
{}
    [SEARCH API]:
    UID: {}
    SECRET: {}
    URL: {}

    [ASM API]:
    KEY: {}
    URL: {}
    """.format(msg_icons["list"], "-" * 50, api["uid"], api["secret"], api["url"], api["asm_key"], api["asm_url"]))
    sys.exit(0)


def _get_asm_hosts(filter_tags=None):
    global api
    global msg_icons

    targets = []
    print(msg_icons["ok"], "Collecting ASM assets")

    # Fetch all hosts
    query = "{}/{}".format(api["asm_url"], "assets/hosts")
    headers = {"Accept": "application/json", "Censys-Api-Key": api["asm_key"]}

    res = req.get(query, headers=headers)
    data = res.json()

    if res.status_code != 200:
        print(msg_icons["err"], "An error occured:", data["error"])
        sys.exit(1)
    else:
        for a in data["assets"]:
            if filter_tags:
                asset_tags = [at["name"] for at in a["tags"]]
                if set(filter_tags) & set(asset_tags):
                    targets.append(a["assetId"])
            else:
                targets.append(a["assetId"])

    print(msg_icons["ok"], "Found {} stored assets in ASM".format(len(targets)))

    if len(targets) > 0: 
        return targets
    else:
        print(msg_icons["warn"], "No assets were found, quitting.")
        sys.exit(0)


def _get_search_results(search_query, hosts):
    global api
    global msg_icons

    # Combine search string with available ASM hosts
    q = "(ip:{}) AND {}".format(" OR ip:".join(hosts), search_query)
    api_endpoint = "{}/{}".format(api["url"], "search/ipv4")
    api_query = {"query": q, "fields": ["ip"]}

    res = req.post(api_endpoint, json=api_query, auth=(api["uid"], api["secret"]))
    data = res.json()

    if res.status_code == 429:
        print(msg_icons["warn"], "Rate limit exceeded!")
        sys.exit(1)
    elif res.status_code == 400:
        print(msg_icons["err"], "Query could not ber parsed")
        sys.exit(1)
    elif res.status_code != 200:
        print(msg_icons["err"], "An error occured:", data["error"])
        sys.exit(1)
    else:
        print(msg_icons["ok"], "Found {} results:".format(len(data["results"])))

        if len(data["results"]) > 0:
            for asset in data["results"]:
                print(msg_icons["list"], "\t", asset["ip"])
        
        print(msg_icons["ok"], "Query complete, quitting")
        sys.exit(0)


def search(query, asset_filter):
    targets = _get_asm_hosts(asset_filter)
    results = _get_search_results(search_query=query, hosts=targets)

    


if __name__ == "__main__":
    api = {"uid": None, "secret": None, "url": None, "asm_key": None,  "asm_url": None}
    msg_icons = {"ok": "[+]", "fail": "[-]", "warn": "[!]", "err": "[x]", "list": "[*]"}
    main()

