import requests
import json
import time
import os

# Standby mode actor ("Faster")

"""
The Standby mode is a new, lightweight method for using Actors. 
Instead of starting an Actor for each input and waiting for results, 
the Actor remains ready in the background to handle arbitrary HTTP requests, 
just like any web or API server.
"""

APIFY_USER_ID = 0 # get it from env
APIFY_API_TOKEN = 0 # get it from env
ACTOR_ID = 0 # get it from env

url_apify = "https://api.apify.com/v2/acts/"

url_actor = 0 # get it from env

url_listing = "https://www.idealista.pt/imovel/33970891/"

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {APIFY_API_TOKEN}"
}

data = {
    "Url": url_listing,
    "proxyConfig": {
        "useApifyProxy": True,
        "apifyProxyGroups": ["RESIDENTIAL"]
    }
}

response = requests.post(url_actor, headers=headers, json=data)
property_data = response.json()
print(property_data)