from DrissionPage import ChromiumPage, ChromiumOptions
from curl_cffi import requests
import os
import time
import urllib.parse
import urllib.parse as urlparse
import json
import re
import traceback
from database import *
from bs4 import BeautifulSoup
import threading

def get_browser():
    # first get the initial html, cookies and local storage
    # check the os and set the browser path
    if os.name == 'nt':
        browser_path = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
    else:
        browser_path = "/usr/bin/google-chrome-stable"

    op = ChromiumOptions().set_browser_path(browser_path)
    # op.headless(True)
    op.auto_port()
    page = ChromiumPage(op)
    return page

BROWSER = get_browser()
BROWSER.get("https://www.tiktok.com/")
# time.sleep(10)

def get_current_epoch():
    current_epoch_ms = int(time.time() * 1000)
    print(f"Current epoch timestamp (milliseconds): {current_epoch_ms}")
    return current_epoch_ms

def js_request(browser, url, referer):
    js_script = '''
                return fetch("''' + url + '''"
            '''
    js_script += '''
                    , {
                    "headers": {
                        "accept": "*/*",
                        "accept-language": "en-US,en;q=0.9,bn;q=0.8",
                        "priority": "u=1, i",
                        "sec-ch-ua": "\\"Brave\\";v=\\"129\\", \\"Not=A?Brand\\";v=\\"8\\", \\"Chromium\\";v=\\"129\\"",
                        "sec-ch-ua-mobile": "?0",
                        "sec-ch-ua-platform": "\\"Windows\\"",
                        "sec-fetch-dest": "empty",
                        "sec-fetch-mode": "cors",
                        "sec-fetch-site": "same-origin",
                        "sec-gpc": "1"
                    },
                    "referrer": "''' + referer + '''",
                    "referrerPolicy": "strict-origin-when-cross-origin",
                    "body": null,
                    "method": "GET",
                    "mode": "cors",
                    "credentials": "include"
                    })
                '''
    response = browser.run_js_loaded(js_script)
    print(f"Response: {response}")
    response = json.loads(response) if type(response) == str else response
    with open(f"sample_data/response.{get_current_epoch()}.html", "w", encoding="utf-8") as f:
        f.write(str(response))
    # save the response to a file
    with open(f"sample_data/response.{get_current_epoch()}.json", "w", encoding="utf-8") as f:
        json.dump(response, f, indent=4)
    return response

def structure_keyword_data(search_results):
    final_results = []
    for search_result in search_results:
        if search_result['type'] != 1:
            continue
        
        video_id = search_result['item']['video']['id']
        author_username = search_result['item']['author']['uniqueId']
        video_url = "https://www.tiktok.com/@" + author_username + "/video/" + video_id
        video_caption = search_result['item']['desc']
        print(f"Video URL: {video_url}")

        # threading.Thread(target=get_author_data, args=(author_username, video_id, db)).start()

        final_results.append({
            "video_id": video_id,
            "video_url": video_url,
            "video_caption": video_caption,
            "author_username": author_username,
            "search_type": "keyword"
        })
    return final_results

def structure_hashtag_data(search_results):
    final_results = []
    for search_result in search_results:        
        video_id = search_result['video']['id']
        author_username = search_result['author']['uniqueId']
        video_url = "https://www.tiktok.com/@" + author_username + "/video/" + video_id
        video_caption = search_result['desc']

        print(f"Video URL: {video_url}")

        # threading.Thread(target=get_author_data, args=(author_username, video_id, db)).start()

        final_results.append({
            "video_id": video_id,
            "video_url": video_url,
            "video_caption": video_caption,
            "author_username": author_username,
            "search_type": "hashtag"
            })
    return final_results

def parse_video_url(video_url, changed_data):   
    for key in changed_data:
        # use regex to replace the key value pair
        video_url = re.sub(rf"{key}=[^&]+", f"{key}={changed_data[key]}", video_url)

    return video_url


def scrape_keyword_videos(query, db):
    try:
        browser = get_browser()
        encoded_keyword = urllib.parse.quote(query)
        URL = f"https://www.tiktok.com/search?q={encoded_keyword}&t={get_current_epoch()}"
        print(f"Scraping URL: {URL}")
        browser.listen.start('search/general/full/')
        browser.get(URL)
        request_url = None
        response_data = None
        has_more = 1
        cursor = 0
        
        while has_more:
            for request in browser.listen.steps():
                request_url = request.url
                print(f"Request URL: {request_url}")
                response_data = json.loads(request._raw_body)
                # save to a file
                with open(f"sample_data/response.{get_current_epoch()}.json", "w", encoding="utf-8") as f:
                    json.dump(response_data, f, indent=4)
                has_more = response_data['has_more']
                cursor = response_data['cursor']
                scrolling_retry = 0
                scraping_ended = False
                while scrolling_retry < 3:
                    # if No more results in html body, break
                    soup = BeautifulSoup(browser.html, 'html.parser')
                    if soup.body and "No more results".lower() in soup.body.get_text().lower():
                        has_more = 0
                        break
                    try:
                        processed_data = structure_keyword_data(response_data['data'])
                        db.insert_many(processed_data)
                        browser.run_js_loaded('document.querySelector(\'[data-e2e="search_top-item-list"]\').lastChild.scrollIntoView({ behavior: "smooth" })')
                        break
                    except:
                        print(traceback.format_exc())
                        # get the div with data-e2e="search_top-item-list"'s last child
                        browser.run_js_loaded('document.querySelector(\'[data-e2e="search_top-item-list"]\').firstChild.scrollIntoView({ behavior: "smooth" })')
                        time.sleep(2)
                        browser.run_js_loaded('document.querySelector(\'[data-e2e="search_top-item-list"]\').lastChild.scrollIntoView({ behavior: "smooth" })')
                        time.sleep(2)
                        scrolling_retry += 1
                        if scrolling_retry == 3:
                            scraping_ended = True
                            break
                if scraping_ended:
                    has_more = 0
                    break
                time.sleep(2)
            
        browser.listen.stop()
        browser.close()
    except KeyboardInterrupt:
        print("Keyboard interrupt detected. Exiting...")

def scrape_hashtag_videos(hashtag, db):
    try:
        browser = get_browser()
        URL = f"https://www.tiktok.com/tag/{hashtag}"
        print(f"Scraping URL: {URL}")
        browser.listen.start('api/challenge/item_list')
        browser.get(URL)
        request_url = None
        response_data = None
        has_more = True
        cursor = 0
        
        while has_more:
            print(f"Cursor: {cursor}")
            for request in browser.listen.steps():
                request_url = request.url
                print(f"Request URL: {request_url}")
                response_data = json.loads(request._raw_body)
                # save to a file
                with open(f"sample_data/response.{get_current_epoch()}.json", "w", encoding="utf-8") as f:
                    json.dump(response_data, f, indent=4)
                has_more = response_data['hasMore']
                cursor = response_data['cursor']
                scrolling_retry = 0
                scraping_ended = False
                print(f"Has more: {has_more}")
                while scrolling_retry < 3:
                    print("Scrolling retry: ", scrolling_retry)
                    # if No more results in html body, break
                    soup = BeautifulSoup(browser.html, 'html.parser')
                    if soup.body and "No more results".lower() in soup.body.get_text().lower():
                        has_more = 0
                        break
                    try:
                        print(len(response_data['itemList']))
                        processed_data = structure_hashtag_data(response_data['itemList'])
                        db.insert_many(processed_data)
                        time.sleep(1)
                        browser.run_js_loaded('''document.querySelector('[data-e2e="challenge-item-list"]').lastChild.scrollIntoView({ behavior: "smooth" })''')
                        break
                    except:
                        print(traceback.format_exc())
                        # get the div with data-e2e="challenge-item-list"'s last child
                        browser.run_js_loaded('''document.querySelector('[data-e2e="challenge-item-list"]').firstChild.scrollIntoView({ behavior: "smooth" })''')
                        time.sleep(2)
                        browser.run_js_loaded('''document.querySelector('[data-e2e="challenge-item-list"]').lastChild.scrollIntoView({ behavior: "smooth" })''')
                        time.sleep(2)
                        scrolling_retry += 1
                        if scrolling_retry == 3:
                            scraping_ended = True
                            break
                if scraping_ended:
                    has_more = 0
                    break
                time.sleep(2)
                ###
                break
            
        
    except KeyboardInterrupt:
        print("Keyboard interrupt detected. Exiting...")
    finally:
        try:
            browser.listen.stop()
            try:
                browser.close()
            except:
                pass
        except:
            pass

def get_author_data(browser, author_username, video_id, db):
    try:
        global BROWSER
        BROWSER.get(f"https://www.tiktok.com/@{author_username}")
        html = browser.html
        # save to a file
        with open(f"sample_data/author_response.{get_current_epoch()}.html", "w", encoding="utf-8") as f:
            f.write(str(html))
        followers = re.search(r"followerCount\":(\d+)", str(html)).group(1)
        following = re.search(r"followingCount\":(\d+)", str(html)).group(1)
        likes = re.search(r"heartCount\":(\d+)", str(html)).group(1)
        browser.close()
        # search for the video id in database and update the author data
        db.update({"video_id": video_id}, {"$set": {"author_data": { "username": author_username, "followers": followers, "following": following, "likes": likes }}})
    except:
        print(traceback.format_exc())
        pass
    finally:
        try:
            browser.close()
        except:
            pass

if __name__ == "__main__":
    db = Database()
    # scrape_hashtag_videos("traveltok", db)
    get_author_data(BROWSER, "https://www.tiktok.com/@mdshajibbhuiyan302", "7310561750833728774", db)
