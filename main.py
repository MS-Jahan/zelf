from DrissionPage import ChromiumPage, ChromiumOptions
import os
import urllib.parse
from helpers import *
from database import Database
from concurrent.futures import ThreadPoolExecutor

db = Database()

keywords_to_search = [
    "beautiful destinations",
    "places to visit",
    "places to travel",
    "places that don't feel real",
    "travel hacks"
]

hashtags_to_search = [
    "traveltok",
    "wanderlust",
    "backpackingadventures",
    "luxurytravel",
    "hiddengems",
    "solotravel",
    "roadtripvibes",
    "travelhacks",
    "foodietravel",
    "sustainabletravel"
]

def process_keyword(keyword):
    try:
        scrape_keyword_videos(keyword, db)
    except Exception as e:
        print(f"Error in keyword '{keyword}': {e}")

def process_hashtag(hashtag):
    try:
        scrape_hashtag_videos(hashtag, db)
    except Exception as e:
        print(f"Error in hashtag '{hashtag}': {e}")

with ThreadPoolExecutor(max_workers=2) as executor:
    executor.map(process_keyword, keywords_to_search)
    executor.map(process_hashtag, hashtags_to_search)
